import streamlit as st
import pandas as pd
from utilities.db_operations import clear_cache, get_connection, load_data
from utilities import calculations


def run(dev_run):
    def nav_button(label, target, action):
        clicked = st.sidebar.button(label, use_container_width=True, on_click=action)
        if clicked:
            st.session_state.page = target

    st.set_page_config(initial_sidebar_state="collapsed", layout="wide")

    col1, col2 = st.columns(2)
    with col1:
        st.title("My finances")
    with col2:
        # Create custom CSS for right-aligned button
        st.markdown("""
                    <style>
                    div.stButton > button {
                        float: right;
                    }
                    </style>
                    """, unsafe_allow_html=True)
        if st.button("🔄 Refresh Data"):
            clear_cache()
            st.rerun()
    st.write("")
    st.write("")

    engine = get_connection()
    df = load_data(engine)
    st.session_state["df"] = df

    calculations.salary(df)
    calculations.investments(df)
    # display()


if __name__ == '__main__':
    run(dev_run=True)
