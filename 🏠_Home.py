import streamlit as st

from utilities import calculations
from utilities.auth import require_auth


def main():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    require_auth(dev_run=False)

    df = st.session_state.get("df")
    usd = st.session_state.get("usd")
    pln = st.session_state.get("pln")

    marginl, center, marginr = st.columns([1, 8, 1])
    with center:
        col_1, col_2, col_3 = st.columns([23, 12, 4])
        with col_1:
            st.header("Overview")
            st.write("")
        with col_2:
            st.write("")
            start = st.segmented_control(None, ["1M", "3M", "6M", "YTD", "1Y", "∞"], default='YTD', selection_mode='single')
            df = calculations.find_start(df, start)
        with col_3:
            st.write("")
            curr = st.segmented_control(None, ['zł', '€'], default='zł', selection_mode="single")

        st.write("")

    def salary(df):
        df = df[df["stock"] == 'Salary']

        marginl, center, marginr = st.columns([1, 8, 1])
        with center:
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
        marginl, center, marginr = st.columns([1, 8, 1])
        with center:
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
    main()
