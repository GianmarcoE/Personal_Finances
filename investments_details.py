import datetime
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.colors import qualitative
from utilities import calculations
from utilities.auth import require_auth
from utilities.db_operations import clear_cache


def modern_portfolio_chart(df):
    """
    Modern, clean portfolio line chart with positive/negative areas.
    """
    y_values = df.iloc[:, 0]
    x_values = df.index

    fig = go.Figure()

    # --- Segment containers ---
    pos_segments = []
    neg_segments = []

    cur_x, cur_y = [], []
    cur_sign = None

    for i in range(len(y_values)):
        sign = y_values[i] >= 0

        if cur_sign is None:
            cur_sign = sign

        # Detect sign change
        if sign != cur_sign and i > 0:
            # Interpolate zero crossing
            y0, y1 = y_values[i - 1], y_values[i]
            x0, x1 = x_values[i - 1], x_values[i]
            t = -y0 / (y1 - y0)
            x_cross = x0 + (x1 - x0) * t

            cur_x.append(x_cross)
            cur_y.append(0)

            if cur_sign:
                pos_segments.append((cur_x, cur_y))
            else:
                neg_segments.append((cur_x, cur_y))

            cur_x = [x_cross]
            cur_y = [0]
            cur_sign = sign

        cur_x.append(x_values[i])
        cur_y.append(y_values[i])

    # Final segment
    if cur_x:
        (pos_segments if cur_sign else neg_segments).append((cur_x, cur_y))

    # --- Positive segments ---
    for x, y in pos_segments:
        fig.add_trace(go.Scatter(
            x=x,
            y=y,
            mode="lines",
            line=dict(color="#22c55e", width=3, shape="spline"),
            fill="tozeroy",
            fillcolor="rgba(34,197,94,0.12)",
            hovertemplate="<b>%{x|%d %b %Y}</b><br>€ %{y:,.2f}<extra></extra>",
            showlegend=False
        ))

    # --- Negative segments ---
    for x, y in neg_segments:
        fig.add_trace(go.Scatter(
            x=x,
            y=y,
            mode="lines",
            line=dict(color="#ef4444", width=3, shape="spline"),
            fill="tozeroy",
            fillcolor="rgba(239,68,68,0.12)",
            hovertemplate="<b>%{x|%d %b %Y}</b><br>€ %{y:,.2f}<extra></extra>",
            showlegend=False
        ))

    # --- Layout: slick, clean, tech ---
    fig.update_layout(
        height=360,
        margin=dict(l=0, r=0, t=0, b=20),
        hovermode="x unified",

        xaxis=dict(
            showgrid=False,
            zeroline=False,
            tickformat="%b %Y",
            ticks="outside",
            ticklen=6
        ),

        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.05)",
            zeroline=True,
            zerolinecolor="rgba(255,255,255,0.25)",
            zerolinewidth=1,
            tickformat=".,0f"
        ),
    )

    return fig


def create_unique_labels(stocks_df):
    """
    Create unique labels for stocks that might have duplicates
    """
    unique_labels = []
    label_counts = {}

    for _, row in stocks_df.iterrows():
        base_label = row['stock'][:8]

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
        if max_value > 0:
            graph_range = [0, max_value * 1.2]
        else:
            max_value = stocks["earning"].min()
            color = "#ef4444"
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

    if len(stocks) != 0:
        unique_labels = create_unique_labels(stocks)
    else:
        unique_labels = ['']
    if len(stocks) == 3:
        width = 0.4
    elif len(stocks) == 2:
        width = 0.3
    else:
        width = 0.15

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
        texttemplate="%{y:.0f}",  # ← integer display
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
            x=0.225,  # Center the title
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
        margin=dict(l=30, r=30, t=50, b=60),
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
            x=0.16,
            font=dict(size=15, family='Arial', color='#b8b6b6')
        ),
        height=310,
        showlegend=False,
        paper_bgcolor='#1e1e1e',  # Match background
        plot_bgcolor='#1e1e1e'
    )

    return fig


def heatmap(daily):
    daily["date"] = pd.to_datetime(daily["date_sell"])
    daily["dow"] = daily["date"].dt.weekday  # 0=Mon
    daily["week"] = daily["date"].dt.isocalendar().week
    daily["year"] = daily["date"].dt.year

    daily["week_index"] = (
            daily["date"]
            - pd.to_timedelta(daily["dow"], unit="D")
    ).dt.isocalendar().week

    daily = daily[daily["dow"] < 5]

    calendar = daily.pivot_table(
        index="dow",
        columns="week_index",
        values="earning",
        aggfunc="sum"
    )

    calendar = calendar.reindex(index=range(5))  # Force Mon–Fri rows

    # Get actual min and max values
    min_val = calendar.values.min() if not pd.isna(calendar.values.min()) else 0
    max_val = calendar.values.max() if not pd.isna(calendar.values.max()) else 0

    # Calculate the position of zero in the scale (0 to 1)
    total_range = max_val - min_val
    zero_position = (0 - min_val) / total_range if total_range > 0 else 0.5

    fig = go.Figure(
        go.Heatmap(
            z=calendar.values,
            x=[f"W{w}" for w in calendar.columns],
            y=["Mon", "Tue", "Wed", "Thu", "Fri"],
            colorscale=[
                [0.0, "#ef4444"],  # Deep red at min_val
                [zero_position * 0.5, "#882020"],  # Mid-dark red
                [zero_position * 0.9, "#241919"],  # Dark red approaching zero
                [max(0, zero_position - 0.01), "#1E1E1E"],  # Background just before zero
                [zero_position, "#1E1E1E"],  # Background at zero
                [min(1, zero_position + 0.01), "#1E1E1E"],  # Background just after zero
                [zero_position + (1 - zero_position) * 0.1, "#19241a"],  # Dark green leaving zero
                [zero_position + (1 - zero_position) * 0.5, "#0d7a57"],  # Mid-dark green
                [1.0, "#10b981"],  # Bright green at max_val
            ],
            zauto=False,
            zmin=min_val,
            zmax=max_val,
            # REMOVED zmid=0 - this was causing the problem!
            hovertemplate="<b>%{x}</b><br>%{y}<br>P/L: <b>€%{z:,.2f}</b><extra></extra>",
            showscale=False,
            colorbar=dict(
                thickness=10,
                len=0.7,
                x=1.02,
                tickformat="€.,0f",
                tickfont=dict(size=10, color='#9ca3af'),
                outlinewidth=0
            ),
            xgap=4,
            ygap=6,
        )
    )

    fig.update_layout(
        height=80,
        margin=dict(l=10, r=30, t=0, b=10),
        xaxis=dict(
            showgrid=False,
            showticklabels=False,
            zeroline=False,
            type='category'
        ),
        yaxis=dict(
            showgrid=False,
            side='left',
            tickfont=dict(size=11, color='#9ca3af'),
            type='category',
            autorange='reversed'
        ),
        plot_bgcolor='#1e1e1e',
        paper_bgcolor='#1e1e1e',
        font=dict(family='Arial')
    )

    return fig


if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
require_auth(dev_run=False)

# Retrieve df
df = st.session_state.get("df")
df = df[~df["stock"].isin(["Salary", "Savings"])]
df["owner"] = "Gim"
usd_rate = st.session_state.get("usd")
pln_rate = st.session_state.get("pln")

marginleft, col1, col2, marginright = st.columns([2, 11, 5, 2])
with col1:
    st.header(f"Trading Portfolio", anchor=False)
with col2:
    st.write("")
    start = st.segmented_control(None, ["1M", "3M", "6M", "YTD", "1Y", "∞"], default='YTD', selection_mode='single')

st.write("")
df = calculations.find_start(df, start)

today = datetime.date.today()

marginleft, col1, col2, col3, marginright = st.columns([1, 4, 2, 2, 1])
with col1:
    with st.expander("Settings ⚙️", expanded=False):
        col_1, col_2 = st.columns(2)
        with col_1:
            include_dividends = st.toggle("Incl. dividends", value=True, key="include_dividends")
        with col_2:
            include_open = st.toggle("Incl. open positions", value=False, key="include_open")
        st.divider()
        col_1, col_2 = st.columns(2)
        with col_1:
            if st.button("➕ Add transaction", width='stretch'):
                calculations.add_transaction_dialog('A', df, today)
        with col_2:
            if st.button("✔️ Modify open position", width='stretch'):
                calculations.add_transaction_dialog('B', df, today)
        col_1, col_2, col_3 = st.columns([1, 2, 1])
        with col_2:
            if st.button("🔄 Refresh Data", width='stretch'):
                clear_cache()
                st.rerun()
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
stats = owner_stats['Gim']

with col3:
    # Create card styling
    earnings_color = "green" if stats["total_earnings"] >= 0 else "#d61111"
    worst_color = "green" if stats["worst_trade"] >= 0 else "#d61111"
    if stats['best_trade'] < 0:
        stats['best_trade'] = 0
    else:
        stats['best_trade'] = stats['best_trade']
    if stats['worst_trade'] > 0:
        stats['worst_trade'] = 0
    else:
        stats['worst_trade'] = stats['worst_trade']

    st.markdown(f"""
    <div style="
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 15px 20px 15px;
        background-color: #222;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    ">
        <div style="display: flex; flex-direction: column; gap: 8px;">
            <div><strong>💰 Total Earnings:</strong> 
                <span style="color: {earnings_color}">€{stats['total_earnings']:.2f}</span>
            </div>
            <div><strong>📅 Avg. Hold Time:</strong> {stats['avg_holding_days']:.0f} days</div>
            <div><strong>🎯 Win Rate:</strong> {stats['win_rate']:.1f}%</div>
            <div><strong>📊 Transactions:</strong> {stats['total_transactions']}</div>
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
    top_3 = (
        closed_transactions
        .query("earning > 0")
        .nlargest(3, "earning")[["stock", "earning"]]
    )
    worst_3 = (
        closed_transactions
        .query("earning < 0")
        .nsmallest(3, "earning")[["stock", "earning"]]
    )

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

    capital = calculations.find_capital(chart_data, usd_rate, pln_rate)
    # Create chart data
    daily = calculations.create_daily_cumulative(chart_data)
    chart_df = daily.pivot(index="date_sell", columns="owner", values="cumulative").ffill()

    with col1:
        percentage_return = round(stats['total_earnings'] * 100 / capital, 2)
        color = 'rgba(34,197,94,1)' if percentage_return >= 0 else 'rgba(239,68,68,1)'  # Green or red text
        sign = '+' if percentage_return >= 0 else ''
        st.markdown(
            f"Total Earnings: <span style='color: {color}; "
            f"background-color: rgba(34,197,94,0.12);"
            f"padding: 2px 6px; border-radius: 4px;'>{sign}{percentage_return}%</span>",
            unsafe_allow_html=True
        )
        chart_df.index = pd.to_datetime(chart_df.index)
        fig = modern_portfolio_chart(chart_df)
        st.plotly_chart(fig, width='stretch')

        # with st.expander("Show all transactions details", expanded=False):
        @st.dialog("Daily P/L")
        def all_transactions():
            st.plotly_chart(heatmap(daily), width='stretch', config={"displayModeBar": False})
            st.dataframe(open_df.drop(columns=["id", "ticker", "owner", "quantity_buy", "price_sell", "quantity_sell",
                                               "total_buy", "total_sell", "price_buy"]),
                         hide_index=True, column_config=
                         {
                             "stock": st.column_config.TextColumn("Stock"),
                             "date_buy": st.column_config.DateColumn("Buy Date"),
                             "date_sell": st.column_config.DateColumn("Sell Date"),
                             "currency": st.column_config.TextColumn("Currency"),
                             "dividends": st.column_config.NumberColumn("Dividends", format="%.2f"),
                             "earning": st.column_config.NumberColumn("Earnings", format="%.2f €"),
                         }
                         )

        if st.button("See all transactions", width='stretch'):
            all_transactions()

    with col2:
        st.plotly_chart(fig_best, width='stretch')
        st.plotly_chart(fig_worst, width='stretch')
    with col3:
        st.write("")
        st.plotly_chart(fig_ring, width='stretch')
else:
    st.info("Select at least one owner to view data.")

# News section
open_df = open_df[open_df["date_sell"] == "OPEN"]
# Get unique tickers for open positions
open_tickers = open_df["ticker"].unique()[:3]

news_by_ticker = {}
for ticker in open_tickers:
    # Try to get a valid news item (with retries if needed)
    max_attempts = 5  # Try up to 5 news articles
    for attempt in range(max_attempts):
        news = calculations.get_one_news(ticker, index=attempt)

        # If no more news available, break
        if not news:
            break

        # Validate that news has the expected structure AND a valid link
        if isinstance(news, dict) and news.get('content'):
            content = news.get('content', {})
            click_through = content.get("clickThroughUrl") or {}
            link = click_through.get("url") if isinstance(click_through, dict) else None

            # Check if we have a valid link
            if link and link != "#" and link.startswith("http"):
                news_by_ticker[ticker] = news
                break  # Found valid news, stop trying

if news_by_ticker:
    marginl, center, marginr = st.columns([1, 8, 1])
    with center:
        st.subheader("📰 Latest News", anchor=False)

    cols = st.columns([3, 8, 8, 8, 3])

    for col, (ticker, item) in zip(cols[1:-1], news_by_ticker.items()):
        with col:
            # Safely extract nested values with defaults
            content = item.get('content') or {}
            title = content.get("title") or "No title"

            # Safely get nested clickThroughUrl
            click_through = content.get("clickThroughUrl") or {}
            link = click_through.get("url") if isinstance(click_through, dict) else "#"
            if not link:
                link = "#"

            # Safely get thumbnail
            thumbnail = content.get("thumbnail") or {}
            thumbnail_url = thumbnail.get("originalUrl") if isinstance(thumbnail, dict) else ""

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
