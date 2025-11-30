import datetime
import pandas as pd
import streamlit as st
import requests
import yfinance as yf
import json
import plotly.graph_objects as go


@st.cache_data(ttl=600)  # Cache for 10 minute
def get_current_prices(df_filtered):
    """Get current prices with caching"""
    if df_filtered.empty:
        return df_filtered
    return api_current_price(df_filtered.copy())


def create_daily_cumulative(df):
    """Create daily cumulative data"""
    daily = df.groupby(["owner", "date_sell"])["earning"].sum().reset_index()
    daily = daily.sort_values(["owner", "date_sell"])
    daily["cumulative"] = daily.groupby("owner")["earning"].cumsum()
    return daily


def api_request_fx(currency, transaction_date) -> float:
    try:
        url = f'https://api.frankfurter.dev/v1/{transaction_date}?symbols={currency}'
        r = requests.get(url)
        parsed = json.loads(r.text)
        response = parsed['rates']
        fx_rate = list(response.values())[0]
        return fx_rate
    except Exception as e:
        print(f'Error fetching exchange rate: {str(e)}')


def api_current_price(df):
    # Identify open transactions (no sell date)
    open_mask = df["date_sell"].isna()

    # Get unique tickers for open positions
    open_tickers = df.loc[open_mask, "ticker"].unique()

    if len(open_tickers) == 0:
        return df

    try:
        # Single API call to fetch all current prices
        current_prices = yf.download(
            tickers=list(open_tickers),
            period="1d",
            group_by="ticker",
            auto_adjust=True,
            prepost=True,
            threads=True
        )

        # Extract the most recent close price for each ticker
        ticker_prices = {}

        if len(open_tickers) == 1:
            # Single ticker case - data structure is different
            ticker = open_tickers[0]
            if not current_prices.empty and "Close" in current_prices.columns:
                ticker_prices[ticker] = current_prices["Close"].iloc[-1]
        else:
            # Multiple tickers case
            for ticker in open_tickers:
                try:
                    if ticker in current_prices.columns.get_level_values(0):
                        close_data = current_prices[ticker]["Close"]
                        if not close_data.empty:
                            ticker_prices[ticker] = close_data.iloc[-1]
                except (KeyError, IndexError):
                    print(f"Could not extract price for {ticker}")
                    continue

        # Update dataframe with fetched prices - VECTORIZED
        today = datetime.date.today()

        for ticker, current_price in ticker_prices.items():
            stock_mask = (df["ticker"] == ticker) & open_mask

            # Vectorized operations - no loops
            df.loc[stock_mask, "total_sell"] = current_price * df.loc[stock_mask, "quantity_buy"]
            df.loc[stock_mask, "earning"] = round(df.loc[stock_mask, "total_sell"] - df.loc[stock_mask, "total_buy"], 2)
            df.loc[stock_mask, "date_sell"] = today

        # Convert all earnings to EUR at once (only for updated rows)
        updated_mask = df["ticker"].isin(ticker_prices.keys()) & open_mask
        if updated_mask.any():
            # Call convert_to_eur only on rows that were updated
            df.loc[updated_mask, "earning"] = df.loc[updated_mask].apply(
                lambda row: convert_to_eur(row, "earning", "date_sell"), axis=1
            )

        # Set date_sell to "OPEN" for all updated rows
        df.loc[updated_mask, "date_sell"] = "OPEN"

    except Exception as e:
        # Fallback to original method if bulk fetch fails
        today = datetime.date.today()

        for ticker in open_tickers:
            try:
                current_price = yf.Ticker(ticker).history(period="1d")["Close"].iloc[-1]
                stock_mask = (df["ticker"] == ticker) & open_mask

                df.loc[stock_mask, "total_sell"] = current_price * df.loc[stock_mask, "quantity_buy"]
                df.loc[stock_mask, "earning"] = round(
                    df.loc[stock_mask, "total_sell"] - df.loc[stock_mask, "total_buy"], 2)
                df.loc[stock_mask, "date_sell"] = today
            except Exception as ticker_error:
                pass

        # Convert all earnings to EUR at once in fallback too
        updated_mask = df["date_sell"] == today
        if updated_mask.any():
            df.loc[updated_mask, "earning"] = df.loc[updated_mask].apply(
                lambda row: convert_to_eur(row, "earning", "date_sell"), axis=1
            )
        df.loc[updated_mask, "date_sell"] = "OPEN"

    return df


def convert_to_eur(row, price, date):
    if row["currency"] != "EUR" and not pd.isna(row[date]):
        row[date] = datetime.date.today()
        return round(row[price] / api_request_fx(row["currency"], row[date]), 2)
    return round(row[price], 2)


def convert_open_to_eur(row, price, date, usd_rate, pln_rate):
    if row["currency"] == "USD" and not pd.isna(row[date]):
        return round(row[price] / usd_rate, 2)
    elif row["currency"] == "PLN" and not pd.isna(row[date]):
        return round(row[price] / pln_rate, 2)
    return round(row[price], 2)


def today_rate():
    usd_rate = round(api_request_fx("USD", datetime.date.today()), 2)
    pln_rate = round(api_request_fx("PLN", datetime.date.today()), 2)
    return usd_rate, pln_rate


def create_unique_labels(stocks_df):
    """
    Create unique labels for stocks that might have duplicates
    """
    unique_labels = []
    label_counts = {}

    for _, row in stocks_df.iterrows():
        base_label = row['label']

        # Keep track of how many times we've seen this label
        if base_label in label_counts:
            label_counts[base_label] += 1
            # Add a counter to make it unique
            unique_label = f"{base_label}({label_counts[base_label]})"
        else:
            label_counts[base_label] = 1
            unique_label = base_label

        unique_labels.append(unique_label)

    return unique_labels


def top_worst_graph(is_top, stocks, color, graph_title):
    if is_top:
        max_value = stocks["earning"].max()
        graph_range = [0, max_value * 1.2]
    else:
        max_value = stocks["earning"].min()
        if max_value < 0:
            graph_range = [max_value * 1.2, 0]
        else:
            max_value = stocks["earning"].max()
            color = 'green'
            graph_range = [0, max_value * 1.2]

    fig = go.Figure()

    unique_labels = create_unique_labels(stocks)

    # Add bar trace with modern styling
    fig.add_trace(go.Bar(
        x=unique_labels,
        y=stocks['earning'],
        # Modern color scheme
        marker=dict(
            color=color,  # Modern indigo color
            line=dict(width=0),  # Remove border
            # This creates rounded corners - adjust the radius as needed
            cornerradius=8
        ),
        text=stocks['earning'],
        textposition='outside',  # Position text outside/above the bars
        # Make bars thinner
        width=0.4,  # Adjust this value (0.1 to 1.0) to control bar thickness
        textfont=dict(color='white', size=12, family='Arial')
    ))

    # Update layout for modern appearance
    fig.update_layout(
        title=dict(
            text=graph_title,
            x=0.35,  # Center the title
            font=dict(size=15, family='Arial', color='#b8b6b6')
        ),
        xaxis=dict(
            showgrid=False,
            zeroline=False
        ),
        yaxis=dict(
            showgrid=False,
            showticklabels=False,  # Hide Y-axis scale numbers
            range=[graph_range[0], graph_range[1]],
            visible=False  # Completely hide Y-axis
        ),
        plot_bgcolor='#1E1E1E',
        paper_bgcolor='#1E1E1E',
        font=dict(family='Arial', color='#1f2937'),
        margin=dict(l=40, r=40, t=60, b=50),
        height=300,
        width=300,
        showlegend=False
    )
    return fig


def calculate_metrics(df, include_dividends=True):
    """Calculate derived columns with caching"""
    df = df.copy()
    # Add calculation columns
    df["total_buy"] = df["price_buy"] * df["quantity_buy"]
    df["total_sell"] = df["price_sell"] * df["quantity_sell"] + df['dividends']
    if not include_dividends:
        df["total_sell"] = df["price_sell"] * df["quantity_sell"]
    df["earning"] = df["total_sell"] - df["total_buy"]

    # Convert earnings to EUR
    usd_rate, pln_rate = today_rate()
    df["earning"] = df.apply(lambda row: convert_open_to_eur(row, "earning", "date_sell", usd_rate, pln_rate)
                             , axis=1)
    return df


@st.cache_data
def calculate_owner_stats(df):
    """Calculate statistics for each owner"""
    stats = {}

    for owner in df["owner"].unique():
        owner_df = df[df["owner"] == owner].copy()

        # Closed positions only for most metrics
        closed_df = owner_df[owner_df["date_sell"].notna()]
        open_df = owner_df[owner_df["date_sell"].isna()]

        # Total earnings (closed positions)
        total_earnings = closed_df["earning"].sum() if not closed_df.empty else 0

        # Average position holding time (closed positions only)
        if not closed_df.empty:
            closed_df["date_buy"] = pd.to_datetime(closed_df["date_buy"])
            closed_df["date_sell"] = pd.to_datetime(closed_df["date_sell"])
            closed_df["holding_days"] = (closed_df["date_sell"] - closed_df["date_buy"]).dt.days
            avg_holding_days = closed_df["holding_days"].mean()
        else:
            avg_holding_days = 0

        # Number of transactions
        total_transactions = len(closed_df)
        open_positions = len(open_df)

        # Win rate
        winning_trades = len(closed_df[closed_df["earning"] > 0])
        win_rate = (winning_trades / total_transactions * 100) if total_transactions > 0 else 0

        # Best and worst trade
        best_trade = closed_df["earning"].max() if not closed_df.empty else 0
        worst_trade = closed_df["earning"].min() if not closed_df.empty else 0

        stats[owner] = {
            "total_earnings": total_earnings,
            "avg_holding_days": avg_holding_days,
            "total_transactions": total_transactions,
            "open_positions": open_positions,
            "win_rate": win_rate,
            "best_trade": best_trade,
            "worst_trade": worst_trade,
        }

    return stats


# Retrieve df
df = st.session_state.get("df")
df = df[df["stock"] != 'Salary']
df["owner"] = "Gim"

st.title("Investments Portfolio")
st.write("")

today = datetime.date.today()

col1, col2 = st.columns([2, 1])  # col1 is twice as wide
with col1:
    with st.expander("Settings ⚙️", expanded=False):
        col_1, col_2 = st.columns([2, 5])
        with col_1:
            include_dividends = st.toggle("Include dividends", value=True, key="include_dividends")
        with col_2:
            include_open = st.toggle("Include open positions", value=False, key="include_open")

    st.write("")

# Calculate metrics with caching
df_with_metrics = calculate_metrics(df, include_dividends)

# Calculate owner statistics
owner_stats = calculate_owner_stats(df_with_metrics)

# Get top 3 earners sorted by total_earnings (descending)
top_3_earners = sorted(owner_stats.items(),
                       key=lambda x: x[1]['total_earnings'],
                       reverse=True)[:4]

# Display owner cards
selected_owners = ['Gim']
if selected_owners:
    # Create cards for selected owners
    cards_per_row = len(selected_owners) if len(selected_owners) in [3, 4] else 3  # 4
    rows_needed = (len(selected_owners) + cards_per_row - 1) // cards_per_row

    for row in range(rows_needed):
        cols = st.columns(cards_per_row)
        for i in range(cards_per_row):
            owner_idx = row * cards_per_row + i
            if owner_idx < len(selected_owners):
                owner = selected_owners[owner_idx]
                stats = owner_stats[owner]

                with cols[i]:
                    # Create card styling
                    earnings_color = "green" if stats["total_earnings"] >= 0 else "#d61111"
                    worst_color = "green" if stats["worst_trade"] >= 0 else "#d61111"

                    st.markdown(f"""
                    <div style="
                        border: 1px solid #ddd;
                        border-radius: 10px;
                        padding: 15px;
                        margin: 10px 0;
                        background-color: #222;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    ">
                        <h3 style="margin-top: 0; color: #b8b6b6;">👤 {owner}</h3>
                        <div style="display: flex; flex-direction: column; gap: 8px;">
                            <div><strong>💰 Total Earnings:</strong> 
                                <span style="color: {earnings_color}">€{stats['total_earnings']:.2f}</span>
                            </div>
                            <div><strong>📅 Avg. Hold Time:</strong> {stats['avg_holding_days']:.0f} days</div>
                            <div><strong>🎯 Win Rate:</strong> {stats['win_rate']:.1f}%</div>
                            <div><strong>📊 Transactions:</strong> {stats['total_transactions']} closed, {stats['open_positions']} open</div>
                            <div><strong>🏆 Best Trade:</strong> <span style="color: green">€{stats['best_trade']:.2f}</span></div>
                            <div><strong>📉 Worst Trade:</strong> <span style="color: {worst_color}">€{stats['worst_trade']:.2f}</span></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

    st.write("")

# Filter data
filtered_df = df_with_metrics[df_with_metrics["owner"].isin(selected_owners)] if selected_owners else pd.DataFrame()

# Get current prices only when needed and cache the result
if not filtered_df.empty:
    open_df = get_current_prices(filtered_df)
    closed_transactions = open_df[open_df["date_sell"] != "OPEN"]
    # Show top and worst transactions (only calculate when we have data)
    # if not closed_transactions.empty:
    top_3 = closed_transactions.nlargest(3, 'earning')[['owner', 'stock', 'earning']]
    top_3['label'] = top_3['owner'] + ' - ' + top_3['stock']
    worst_3 = closed_transactions.nsmallest(3, 'earning')[['owner', 'stock', 'earning']]
    worst_3['label'] = worst_3['owner'] + ' - ' + worst_3['stock']

    fig_best = top_worst_graph(True, top_3, 'green', 'Best transactions')
    fig_worst = top_worst_graph(False, worst_3, '#d61111', 'Worst transactions')

    # Handle open positions for chart
    if include_open:
        filtered_df_3 = open_df.copy()
        filtered_df_3.loc[open_df["date_sell"] == "OPEN", "date_sell"] = today
        chart_data = filtered_df_3
    else:
        chart_data = filtered_df

    # Create chart data
    daily = create_daily_cumulative(chart_data)
    chart_df = daily.pivot(index="date_sell", columns="owner", values="cumulative").ffill()

    with col1:
        st.markdown("Total Earnings")
        st.line_chart(chart_df)
        print(chart_df)

        with st.expander("Show all transactions details", expanded=False):
            st.dataframe(open_df.drop(columns=["quantity_buy", "price_sell", "quantity_sell"]),
                         hide_index=True, column_config=
                         {
                             "owner": st.column_config.TextColumn("Owner"),
                             "stock": st.column_config.TextColumn("Stock"),
                             "ticker": st.column_config.TextColumn("Ticker"),
                             "price_buy": st.column_config.NumberColumn("Buy Price"),
                             "total_buy": st.column_config.NumberColumn("Buy tot", format="%.2f"),
                             "date_buy": st.column_config.DateColumn("Buy Date"),
                             "total_sell": st.column_config.NumberColumn("Sell tot", format="%.2f"),
                             "date_sell": st.column_config.DateColumn("Sell Date"),
                             "currency": st.column_config.TextColumn("Currency"),
                             "dividends": st.column_config.NumberColumn("Dividends", format="%.2f"),
                             "earning": st.column_config.NumberColumn("Earnings", format="%.2f €"),
                         }
                         )
        st.write("")

    with col2:
        st.plotly_chart(fig_best, use_container_width=True)
        st.write("")
        st.plotly_chart(fig_worst, use_container_width=True)
        # st.write("")
        # st.plotly_chart(fig_ring, use_container_width=True)
else:
    st.info("Select at least one owner to view data.")