from sqlalchemy import create_engine
import streamlit as st
import pandas as pd


def get_connection():
    # Connect to Neon PostgreSQL
    return create_engine(st.secrets["db_connection"])


# Load current data
@st.cache_data(ttl=600)  # cache results for 5 minutes
def load_data(_engine):
    query = "SELECT * FROM transactions ORDER BY id"
    df = pd.read_sql(query, _engine)
    return df


def clear_cache():
    """Clear all cached data"""
    st.cache_data.clear()


def load_cached_data():
    """Load data from database with caching"""
    engine = get_connection()
    df = load_data(engine)
    return df


# df = load_cached_data()
# df.to_csv(r"C:\Users\gianm\OneDrive\Desktop\finances_db_test")
