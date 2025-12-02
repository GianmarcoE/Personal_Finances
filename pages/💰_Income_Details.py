import streamlit as st
import plotly.express as px


df = st.session_state.get("df")
df = df[df["stock"] == 'Salary']
df["savings"] = df['price_sell'] - df['price_buy']

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("<h3 style='text-align: center;'>Salary</h3>", unsafe_allow_html=True)
    fig = px.bar(df, x="date_buy", y="price_sell", color_discrete_sequence=["green"])
    fig.update_yaxes(range=[-1000, 9000])
    fig.update_layout(
        xaxis_title=None,
        yaxis_title=None,
    )
    st.plotly_chart(fig, use_container_width=True)
with col2:
    st.markdown("<h3 style='text-align: center;'>Expenses</h3>", unsafe_allow_html=True)
    fig = px.bar(df, x="date_buy", y="price_buy", color_discrete_sequence=["red"])
    fig.update_yaxes(range=[-1000, 9000])
    fig.update_layout(
        xaxis_title=None,
        yaxis_title=None,
    )
    st.plotly_chart(fig, use_container_width=True)
with col3:
    st.markdown("<h3 style='text-align: center;'>Savings</h3>", unsafe_allow_html=True)

    # Create a color column based on positive/negative values
    df["color"] = df["savings"].apply(lambda x: "red" if x < 0 else "green")

    fig = px.bar(
        df,
        x="date_buy",
        y="savings",
        color="color",
        color_discrete_map={"red": "red", "green": "green"},
    )

    fig.update_layout(
        showlegend=False,  # hide legend
        xaxis_title=None,
        yaxis_title=None,
    )

    fig.update_yaxes(range=[-1000, 9000])

    st.plotly_chart(fig, use_container_width=True)
