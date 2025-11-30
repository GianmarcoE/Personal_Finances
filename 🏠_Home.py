import streamlit as st
import pandas as pd
from utilities.db_operations import clear_cache, get_connection, load_data
from utilities import calculations


def main(dev_run):
    def nav_button(label, target, action):
        clicked = st.sidebar.button(label, use_container_width=True, on_click=action)
        if clicked:
            st.session_state.page = target

    st.set_page_config(initial_sidebar_state="collapsed", layout="wide")

    col_1, col_2 = st.columns([5, 1])
    with col_1:
        st.title("My finances")
    with col_2:
        if st.button("🔄 Refresh Data"):
            clear_cache()
            st.rerun()
        curr = st.segmented_control('', ['zł', '€'], default='zł', selection_mode="single")

    st.write("")
    st.write("")

    engine = get_connection()
    df = load_data(engine)
    st.session_state["df"] = df

    def salary(df):
        df = df[df["stock"] == 'Salary']

        st.subheader("Income & Expenses")
        total_income = int(df["price_sell"].sum())
        avg_income = int(df["price_sell"].mean())
        expenditures = int(df["price_buy"].sum())
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

    def investments(df):
        st.subheader("Investments")
        df = df[df["stock"] != 'Salary']
        df["owner"] = "Gim"
        df_with_metrics = calculations.calculate_metrics(df, True)
        owner_stats = calculations.calculate_owner_stats(df_with_metrics)
        stats = owner_stats['Gim']

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            calculations.create_card("💰 Total Earnings", stats['total_earnings'], curr)

    salary(df)
    investments(df)


if __name__ == '__main__':
    main(dev_run=True)
