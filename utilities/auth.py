import streamlit as st
import pandas as pd
from utilities.db_operations import get_connection, load_data
from utilities import calculations


def require_auth(dev_run):
    if not st.session_state.get("authenticated", False):
        show_login()
        st.stop()
    if not dev_run:
        engine = get_connection()
        df = load_data(engine)
    else:
        df = pd.read_csv(r"C:\Users\gianm\OneDrive\Desktop\finances_db_test")

    st.session_state["df"] = df
    usd, pln = calculations.today_rate()
    st.session_state["usd"] = usd
    st.session_state["pln"] = pln


def show_login():
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
