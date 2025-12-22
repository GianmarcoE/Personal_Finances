import pandas as pd
import streamlit as st
import requests
import json
import datetime
import yfinance as yf


def find_start(df, start):
    today = datetime.date.today()
    df["date_sell"] = pd.to_datetime(df["date_sell"]).dt.date
    if start == "1M":
        range_start = today - datetime.timedelta(days=30)
    elif start == "3M":
        range_start = today - datetime.timedelta(days=90)
    elif start == "6M":
        range_start = today - datetime.timedelta(days=180)
    elif start == "YTD":
        range_start = datetime.date(today.year, 1, 1)
    elif start == "1Y":
        range_start = today - datetime.timedelta(days=365)
    elif start == "∞":
        return df

    return df[
        (df["date_sell"] >= range_start) |
        (df["date_sell"].isna())
        ]


@st.cache_data(ttl=600)  # Cache for 10 minute
def get_current_prices(df_filtered):
    """Get current prices with caching"""
    if df_filtered.empty:
        return df_filtered
    return api_current_price(df_filtered.copy())


def find_capital(df, usd, pln):
    """
        Calculate the capital pulled into the portfolio, accounting for transaction timing.

        Capital must be pulled if a buy occurs before sufficient sell proceeds are available.
    """
    capital = 0
    available_cash = 0

    # Create a timeline of all buy and sell events
    events = []

    for idx, row in df.iterrows():
        # Add buy event
        events.append({
            'date': row['date_buy'],
            'type': 'buy',
            'amount': abs(row["price_buy"] * row["quantity_buy"]),
            'currency': row['currency']
        })

        # Add sell event if position is closed
        if pd.notna(row['date_sell']):
            events.append({
                'date': row['date_sell'],
                'type': 'sell',
                'amount': abs(row["price_sell"] * row["quantity_sell"] + row["dividends"]),
                'currency': row['currency']
            })

        # Sort all events chronologically
    events_sorted = sorted(events, key=lambda x: x['date'])

    # Process events in chronological order
    for event in events_sorted:
        if event['currency'] == 'USD':
            event['amount'] /= usd
        elif event['currency'] == 'PLN':
            event['amount'] /= pln

        if event['type'] == 'buy':
            # Check if we have enough cash from previous sells
            if available_cash < event['amount']:
                # Need to pull new capital
                capital += event['amount'] - available_cash
                available_cash = 0
            else:
                # Can cover with existing cash
                available_cash -= event['amount']

        elif event['type'] == 'sell':
            # Add proceeds to available cash
            available_cash += event['amount']

    return round(capital)


def create_daily_cumulative(df):
    """Create daily cumulative data"""
    daily = df.groupby(["owner", "date_sell"])["earning"].sum().reset_index()
    daily = daily.sort_values(["owner", "date_sell"])
    daily["cumulative"] = daily.groupby("owner")["earning"].cumsum()
    return daily


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


def create_card(title, value, curr):
    value_formatted = f"{value:,.0f}".replace(",", ".")
    card = st.markdown(f"""
                        <div style="
                            border: 1px solid #ddd;
                            border-radius: 10px;
                            padding: 15px;
                            margin: 10px 0;
                            background-color: #222;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        ">
                            <h4 style="margin-top: 0; color: #b8b6b6;">{title}</h4>
                            <div style="display: flex; justify-content: flex-end;">
                                <div style="font-size: 28px; color: white;">
                                    {value_formatted} {curr}
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
    return card


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


def calculate_metrics(df, usd_rate, pln_rate, include_dividends=True):
    """Calculate derived columns with caching"""
    df = df.copy()
    # Add calculation columns
    df["total_buy"] = df["price_buy"] * df["quantity_buy"]
    df["total_sell"] = df["price_sell"] * df["quantity_sell"] + df['dividends']
    if not include_dividends:
        df["total_sell"] = df["price_sell"] * df["quantity_sell"]
    df["earning"] = df["total_sell"] - df["total_buy"]

    df["earning"] = df.apply(lambda row: convert_open_to_eur(row, "earning", "date_sell", usd_rate, pln_rate), axis=1)
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
        st.session_state["total_earnings"] = total_earnings

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


def toggle_form(form_name):
    if st.session_state.active_form == form_name:
        st.session_state.active_form = None  # Close if already open
    else:
        st.session_state.active_form = form_name  # Open the new form


@st.cache_data(ttl=3600)
def get_one_news(ticker, index=0):
    news = yf.Ticker(ticker).news
    return news[index] if news and len(news) > index else None


@st.dialog("Add transaction")
def add_transaction_dialog(df, today):
    if st.session_state.active_form == "A":
        # Initialize session state for sold checkbox if not exists
        if 'sold_checkbox' not in st.session_state:
            st.session_state.sold_checkbox = False

        # Checkbox outside form with session state
        sold = st.checkbox("Has this stock been sold?", key='sold_checkbox')

        with st.form("form_a"):
            stock = st.text_input("Stock")
            ticker = st.text_input("Ticker (e.g. TSLA)")
            price_buy = st.number_input("Stock buy price", step=0.001)
            quantity_buy = st.number_input("Q.ty", step=0.01)
            date_buy = st.date_input("Date buy", value=today)
            currency = st.selectbox("Currency", ["EUR", "USD", "PLN"])

            # Initialize default values
            price_sell = None
            date_sell = None
            quantity_sell = None
            dividends = 0

            # Show additional fields based on session state
            if st.session_state.sold_checkbox:
                price_sell = st.number_input("Stock sale price", step=0.001)
                quantity_sell = quantity_buy  # changed to avoid manual input
                date_sell = st.date_input("Date sold", value=today)
                dividends = st.number_input("Dividends received", step=0.01)

            if st.form_submit_button("Submit"):
                pass
    elif st.session_state.active_form == "B":
        # SOLUTION 1: Move the owner selection outside the form
        action = st.radio("", ("Close transaction", "Additional Purchase"))

        if action == "Close transaction":
            # Filter open positions for that owner
            open_stocks = df[(df["owner"] == "Gim") & (df["date_sell"].isna())]

            if not open_stocks.empty:
                with st.form("form_b"):
                    # Create selectbox of stock names
                    selected_stock = st.selectbox("Select open stock", open_stocks["stock"].unique())
                    price_sell = st.number_input("Sell Price", step=0.001)
                    date_sell = st.date_input("Date sold", value=today)
                    dividends = st.number_input("Dividends received", step=0.01)

                    if st.form_submit_button("Submit"):
                        pass
        else:
            # Filter open positions for that owner
            open_stocks = df[(df["owner"] == "Gim") & (df["date_sell"].isna())]
            if not open_stocks.empty:
                with st.form("form_b"):
                    # Create selectbox of stock names
                    selected_stock = st.selectbox("Select open stock", open_stocks["stock"].unique())
                    new_price = st.number_input("Buy Price", step=0.001)
                    new_qty = st.number_input("Q.ty", step=0.01)

                    if st.form_submit_button("Submit"):
                        pass
