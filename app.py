import streamlit as st


def info():
    email = st.secrets["email"]
    st.title("Info")
    st.write(f"App developed by Gianmarco Ercolani. For info and support, contact {email}")


pages = [
            st.Page("home.py", title="Home"),
            st.Page("income_details.py", title="Income"),
            st.Page("investments_details.py", title="Investments"),
            st.Page(info, title="Info")
        ]

pg = st.navigation(pages, position="top")
pg.run()
