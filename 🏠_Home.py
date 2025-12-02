import streamlit as st
import pandas as pd
from utilities.db_operations import clear_cache, get_connection, load_data
from utilities import calculations


def main(dev_run):
    st.set_page_config(initial_sidebar_state="collapsed", layout="wide")

    def login():
        if "authenticated" not in st.session_state:
            st.session_state.authenticated = False
        if not st.session_state.authenticated:
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                with st.form("login_form"):
                    st.title("🔐 Login")
                    username = st.text_input("Username")
                    password = st.text_input("Password", type="password")
                    submit = st.form_submit_button("Login")

                if submit:
                    allowed_users = st.secrets["users"]
                    if username in allowed_users and password == allowed_users[username]["password"]:
                        st.session_state.authenticated = True
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
            st.stop()

    login()

    if not dev_run:
        engine = get_connection()
        df = load_data(engine)
    else:
        df = pd.read_csv(r"C:\Users\gianm\OneDrive\Desktop\finances_db_test")

    st.session_state["df"] = df
    usd, pln = calculations.today_rate()
    st.session_state["usd"] = usd
    st.session_state["pln"] = pln

    col_1, col_2 = st.columns([5, 1])
    with col_1:
        st.title("Overview")
    with col_2:
        if st.button("🔄 Refresh Data"):
            clear_cache()
            st.rerun()
        curr = st.segmented_control('', ['zł', '€'], default='zł', selection_mode="single")

    st.write("")
    st.write("")

    def salary(df):
        df = df[df["stock"] == 'Salary']

        st.subheader("Income & Expenses")
        if curr == 'zł':
            total_income = int(df["price_sell"].sum())
            avg_income = int(df["price_sell"].mean())
            expenditures = int(df["price_buy"].sum())
            savings = int(total_income - expenditures)
        else:
            total_income = int(df["price_sell"].sum()/pln)
            avg_income = int(df["price_sell"].mean()/pln)
            expenditures = int(df["price_buy"].sum()/pln)
            savings = int(total_income - expenditures)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            calculations.create_card("💰 Total Income", total_income, curr)
        with col2:
            calculations.create_card("📊 Monthly Avg", avg_income, curr)
        with col3:
            calculations.create_card("💸 Expenses", expenditures, curr)
        with col4:
            calculations.create_card("🏦 Savings", savings, curr)
        st.write("")

    def investments(df, usd, pln):
        st.subheader("Investments")
        df = df[df["stock"] != 'Salary']
        df["owner"] = "Gim"
        df_with_metrics = calculations.calculate_metrics(df, usd, pln, True)
        owner_stats = calculations.calculate_owner_stats(df_with_metrics)
        stats = owner_stats['Gim']
        tax_due = (stats['total_earnings'] * 19)/100
        net_investments = stats['total_earnings'] - tax_due
        if curr == 'zł':
            stats['total_earnings'] *= pln
            tax_due *= pln
            net_investments *= pln

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            calculations.create_card("💰 Total Earnings", stats['total_earnings'], curr)
        with col3:
            calculations.create_card("💸 Tax due", tax_due, curr)
        with col4:
            calculations.create_card("💵 Net balance", net_investments, curr)

    salary(df)
    investments(df, usd, pln)


if __name__ == '__main__':
    main(dev_run=False)
