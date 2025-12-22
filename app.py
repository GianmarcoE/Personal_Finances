import streamlit as st


def info():
    st.title("Info")
    st.write("App developed by Gianmarco Ercolani. For info and support, contact ohohoh@gmail.com")


pages = [
st.Page("home.py", title="Home"),
            st.Page("income_Details.py", title="Income"),
            st.Page("investments_details.py", title="Investments"),
            st.Page(info, title="Info")
            # st.Page("home.py", title="🏠 Home"),
            # st.Page("income_Details.py", title="💰 Income Details"),
            # st.Page("investments_details.py", title="📈 Investments Details"),
            # st.Page(info, title="ℹ️ Info")
        ]

pg = st.navigation(pages, position="top")
pg.run()
