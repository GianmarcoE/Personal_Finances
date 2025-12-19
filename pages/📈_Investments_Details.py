import datetime
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.colors import qualitative
from utilities import calculations
from utilities.auth import require_auth


def create_unique_labels(stocks_df):
    """
    Create unique labels for stocks that might have duplicates
    """
    unique_labels = []
    label_counts = {}

    for _, row in stocks_df.iterrows():
        base_label = row['stock']

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
            color = '#10b981'
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
        margin=dict(l=20, r=20, t=50, b=60),
        height=280,
        width=280,
        showlegend=False
    )
    return fig


def ring_chart(closed_transactions):
    # Group by stock and sum all earnings (so multiple trades are combined)
    stock_summary = (
        closed_transactions
        .groupby('stock', as_index=False)['earning']
        .sum()
    )

    top_4 = stock_summary.nlargest(4, 'earning')
    # Sum of the rest (not in top 4)
    others_sum = stock_summary[~stock_summary['stock'].isin(top_4['stock'])]['earning'].sum()

    labels = list(top_4['stock'])
    values = list(top_4['earning'])

    if others_sum > 0:
        labels.append("Others")
        values.append(others_sum)

    colors = qualitative.Safe[:len(labels)]

    # Create donut chart with modern styling
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.8,
        textinfo='label+percent',
        textposition='outside',
        marker=dict(
            colors=colors,
            line=dict(color='#1e1e1e', width=3)  # Add gap between slices
        ),
        pull=[0.02] * len(labels),  # Slight pull creates separation
        rotation=45  # Rotate for better visual balance
    )])

    fig.update_layout(
        title=dict(
            text="Most profitable stocks",
            x=0.25,
            font=dict(size=15, family='Arial', color='#b8b6b6')
        ),
        height=310,
        showlegend=False,
        paper_bgcolor='#1e1e1e',  # Match background
        plot_bgcolor='#1e1e1e'
    )

    return fig


if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
require_auth(dev_run=False)

# Retrieve df
df = st.session_state.get("df")
df = df[df["stock"] != 'Salary']
df["owner"] = "Gim"
usd_rate = st.session_state.get("usd")
pln_rate = st.session_state.get("pln")

marginleft, col1, col2, marginright = st.columns([2, 11, 5, 2])
with col1:
    st.header("Investments Portfolio")
with col2:
    st.write("")
    start = st.segmented_control(None, ["1M", "3M", "6M", "YTD", "1Y", "∞"], default='YTD', selection_mode='single')
df = calculations.find_start(df, start)
st.write("")

today = datetime.date.today()

marginleft, col1, col2, col3, marginright = st.columns([1, 4, 2, 2, 1])
with col1:
    with st.expander("Settings ⚙️", expanded=False):
        col_1, col_2 = st.columns([2, 5])
        with col_1:
            include_dividends = st.toggle("Include dividends", value=True, key="include_dividends")
        with col_2:
            include_open = st.toggle("Include open positions", value=False, key="include_open")

    st.write("")

# Calculate metrics with caching
df_with_metrics = calculations.calculate_metrics(df, usd_rate, pln_rate, include_dividends)

# Calculate owner statistics
owner_stats = calculations.calculate_owner_stats(df_with_metrics)

# Get top 3 earners sorted by total_earnings (descending)
top_3_earners = sorted(owner_stats.items(),
                       key=lambda x: x[1]['total_earnings'],
                       reverse=True)[:4]

# Display owner cards
selected_owners = ['Gim']
if selected_owners:
    stats = owner_stats['Gim']

    with col3:
        # Create card styling
        earnings_color = "green" if stats["total_earnings"] >= 0 else "#d61111"
        worst_color = "green" if stats["worst_trade"] >= 0 else "#d61111"

        st.markdown(f"""
        <div style="
            border: 1px solid #ddd;
            border-radius: 10px;
            padding: 15px;
            margin: 10px 15px;
            background-color: #222;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        ">
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

# Filter data
filtered_df = df_with_metrics[df_with_metrics["owner"].isin(selected_owners)] if selected_owners else pd.DataFrame()

# Get current prices only when needed and cache the result
if not filtered_df.empty:
    open_df = calculations.get_current_prices(filtered_df)
    closed_transactions = open_df[open_df["date_sell"] != "OPEN"]
    # Show top and worst transactions (only calculate when we have data)
    # if not closed_transactions.empty:
    top_3 = closed_transactions.nlargest(3, 'earning')[['stock', 'earning']]
    worst_3 = closed_transactions.nsmallest(3, 'earning')[['stock', 'earning']]

    fig_best = top_worst_graph(True, top_3, '#10b981', 'Best transactions')
    fig_worst = top_worst_graph(False, worst_3, '#ef4444', 'Worst transactions')
    fig_ring = ring_chart(closed_transactions)

    # Handle open positions for chart
    if include_open:
        filtered_df_3 = open_df.copy()
        filtered_df_3.loc[open_df["date_sell"] == "OPEN", "date_sell"] = today
        chart_data = filtered_df_3
    else:
        chart_data = filtered_df

    # Create chart data
    daily = calculations.create_daily_cumulative(chart_data)
    chart_df = daily.pivot(index="date_sell", columns="owner", values="cumulative").ffill()

    with col1:
        st.markdown("Total Earnings")
        chart_df.index = pd.to_datetime(chart_df.index)
        st.line_chart(chart_df)

        with st.expander("Show all transactions details", expanded=False):
            st.dataframe(open_df.drop(columns=["id", "owner", "quantity_buy", "price_sell", "quantity_sell",
                                               "price_buy"]),
                         hide_index=True, column_config=
                         {
                             "stock": st.column_config.TextColumn("Stock"),
                             "ticker": st.column_config.TextColumn("Ticker"),
                             "total_buy": st.column_config.NumberColumn("Buy tot", format="%.2f"),
                             "date_buy": st.column_config.DateColumn("Buy Date"),
                             "total_sell": st.column_config.NumberColumn("Sell tot", format="%.2f"),
                             "date_sell": st.column_config.DateColumn("Sell Date"),
                             "currency": st.column_config.TextColumn("Currency"),
                             "dividends": st.column_config.NumberColumn("Dividends", format="%.2f"),
                             "earning": st.column_config.NumberColumn("Earnings", format="%.2f €"),
                         }
                         )

    with col2:
        st.plotly_chart(fig_best, use_container_width=True)
        st.plotly_chart(fig_worst, use_container_width=True)
    with col3:
        st.write("")
        st.plotly_chart(fig_ring, use_container_width=True)
else:
    st.info("Select at least one owner to view data.")

# News section
if not open_df.empty:
    open_df = open_df[open_df["date_sell"] == "OPEN"]
    # Get unique tickers for open positions
    open_tickers = open_df["ticker"].unique()[:3]

    news_by_ticker = {}
    for ticker in open_tickers:
        news = calculations.get_one_news(ticker)
        if news:
            news_by_ticker[ticker] = news

    if news_by_ticker:
        marginl, center, marginr = st.columns([1, 8, 1])
        with center:
            st.subheader("📰 Latest news")

        cols = st.columns([3, 8, 8, 8, 3])

        for col, (ticker, item) in zip(cols[1:-1], news_by_ticker.items()):
            with col:
                content = item.get('content', {})
                title = content.get("title", "No title")
                link = content.get("clickThroughUrl", {}).get("url", "#")
                thumbnail_url = content.get("thumbnail", {}).get("originalUrl", "")

                st.markdown(
                    f"""
                    <div style="
                        background-color:#1e1e1e;
                        border-radius:12px;
                        padding:12px;
                        height:380px;
                        box-shadow:0 4px 10px rgba(0,0,0,0.2);
                        display:flex;
                        flex-direction:column;
                        justify-content:space-between;
                        overflow:hidden;
                    ">
                        <div style="font-size:12px;color:#9ca3af;margin-bottom:4px;">{ticker}</div>
                        <div style="
                            font-size:14px;
                            font-weight:600;
                            margin-bottom:6px;
                            white-space: nowrap;
                            overflow: hidden;
                            text-overflow: ellipsis;
                        ">
                            {title}
                        </div>
                        {f'<img src="{thumbnail_url}" style="width:100%; height:200px; object-fit:cover; flex-shrink:0; border-radius:8px; margin-bottom:6px;">' if thumbnail_url else ''}
                        <a href="{link}" target="_blank"
                           style="color:#10b981;font-size:13px;display:block;">
                           Read →
                        </a>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
