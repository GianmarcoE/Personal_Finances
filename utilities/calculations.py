import pandas as pd
import streamlit as st
import datetime


def salary(df):
    df = df[df["stock"] == 'Salary']

    st.subheader("Income & Expenses")
    total_income = int(df["price_sell"].sum())
    avg_income = int(df["price_sell"].mean())
    expenditures = int(df["price_buy"].sum())
    savings = int(total_income - expenditures)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        create_card("💰 Total Income", total_income)
    with col2:
        create_card("📊 Monthly Avg", avg_income)
    with col3:
        create_card("💸 Expenses", expenditures)
    with col4:
        create_card("🏦 Savings", savings)


def investments(df):
    st.subheader("Investments")
    # pages.investments_page.render(df)


def create_card(title, value):
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
                                    {value_formatted} zł
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
    return card
