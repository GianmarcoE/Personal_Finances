import streamlit as st
import plotly.graph_objects as go


def graph(df, date, object, color, height=300):
    fig = go.Figure()
    # Add bar trace with modern styling
    fig.add_trace(go.Bar(
        x=df[date],
        y=df[object],
        # Modern color scheme
        marker=dict(
            color=color,  # Modern indigo color
            line=dict(width=0),  # Remove border
            # This creates rounded corners - adjust the radius as needed
            cornerradius=6
        ),
    ))

    # Update layout for modern appearance
    fig.update_layout(
        bargap=0.5,  # Values from 0 (no gap) to 1 (maximum gap)
        xaxis=dict(
            showgrid=False,
            zeroline=True
        ),
        yaxis=dict(
            showgrid=True,
            showticklabels=True,  # Hide Y-axis scale numbers
            range=[-1000, 9000],
            visible=True  # Completely hide Y-axis
        ),
        plot_bgcolor='#1E1E1E',
        paper_bgcolor='#1E1E1E',
        font=dict(family='Arial', color='#1f2937'),
        margin=dict(l=40, r=40, t=60, b=50),
        height=height,
        showlegend=False
    )
    return fig


def income_expense_graph(df):
    fig = go.Figure()

    # Income bars (positive, going up)
    fig.add_trace(go.Bar(
        x=df["date_buy"],
        y=df["price_sell"],  # Assuming you have an "income" column
        name='Income',
        marker=dict(
            color='#10b981',  # Green for income
            line=dict(width=0),
            cornerradius=8
        ),
    ))

    # Expense bars (negative, going down)
    fig.add_trace(go.Bar(
        x=df["date_buy"],
        y=df["price_buy"],  # Make expenses negative with minus sign
        name='Expenses',
        marker=dict(
            color='#ef4444',  # Red for expenses
            line=dict(width=0),
            cornerradius=8
        ),
    ))

    fig.update_layout(
        barmode='group',  # Places bars side by side
        bargap=0.3,  # Space between date groups
        bargroupgap=0.1,  # Space between income/expense bars
        xaxis=dict(
            showgrid=False,
            zeroline=True
        ),
        yaxis=dict(
            showgrid=True,
            range=[-1000, 9000],
            zeroline=True
        ),
        plot_bgcolor='#1E1E1E',
        paper_bgcolor='#1E1E1E',
        font=dict(family='Arial', color='#e5e7eb'),
        margin=dict(l=40, r=40, t=60, b=50),
        height=300,
        showlegend=False,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    return fig


def cumulative_savings_graph(df):
    # Calculate cumulative sum
    df_cumulative = df.copy()
    df_cumulative["cumulative_savings"] = df_cumulative["savings"].cumsum()

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df_cumulative["date_buy"],
        y=df_cumulative["cumulative_savings"],
        mode='lines+markers',
        line=dict(color='#10b981', width=3),
        marker=dict(size=8, color='#10b981'),
        fill='tozeroy',  # Optional: fills area under the line
        fillcolor='rgba(16, 185, 129, 0.1)'
    ))

    fig.update_layout(
        yaxis=dict(showgrid=True),
        plot_bgcolor='#1E1E1E',
        paper_bgcolor='#1E1E1E',
        font=dict(family='Arial', color='#e5e7eb'),
        margin=dict(l=40, r=40, t=40, b=40),
        height=300,
    )

    return fig


def ring_chart(df):
    # Calculate totals
    total_earnings = df["price_sell"].sum()
    total_savings = df["savings"].sum()
    rest = total_earnings - total_savings

    values = [total_savings, rest]

    # Text only for savings slice, none for rest
    text = ["{:.1%}".format(total_savings / total_earnings), ""]

    fig = go.Figure(data=[go.Pie(
        values=values,
        hole=0.8,
        text=text,                # per-slice text
        textinfo="text",          # use the text list
        marker=dict(colors=["#10b981", "rgba(16, 185, 129, 0.2)"]),
        hoverinfo="none",
        sort=False,
    )])

    fig.update_layout(
        height=250,
        showlegend=False,
        margin=dict(t=20, b=20, l=0, r=0),
    )

    return fig


df = st.session_state.get("df")
df = df[df["stock"] == 'Salary']
df["savings"] = df['price_sell'] - df['price_buy']
df = df.sort_values("date_buy").reset_index(drop=True)

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("<h4 style='text-align: center;'>Salary</h4>", unsafe_allow_html=True)
    fig = graph(df, "date_buy", "price_sell", "#10b981")
    st.plotly_chart(fig, use_container_width=True)
with col2:
    st.markdown("<h4 style='text-align: center;'>Expenses</h4>", unsafe_allow_html=True)
    fig = graph(df, "date_buy", "price_buy", "#ef4444")
    st.plotly_chart(fig, use_container_width=True)
with col3:
    st.markdown("<h4 style='text-align: center;'>Combined</h4>", unsafe_allow_html=True)
    st.plotly_chart(income_expense_graph(df))

st.divider()

col1, col2, col3 = st.columns([3, 2, 3])
with col1:
    # Create a color column based on positive/negative values
    df["color"] = df["savings"].apply(lambda x: "#ef4444" if x < 0 else "#10b981")

    st.markdown("<h4 style='text-align: center;'>Savings</h4>", unsafe_allow_html=True)
    fig = graph(df, "date_buy", "savings", df["color"], 310)
    st.plotly_chart(fig, use_container_width=True)
with col3:
    st.markdown("<h4 style='text-align: center;'>Over time</h4>", unsafe_allow_html=True)
    st.plotly_chart(cumulative_savings_graph(df))
with col2:
    st.markdown("<h4 style='text-align: center;'>As part of earnings</h4>", unsafe_allow_html=True)
    st.plotly_chart(ring_chart(df), use_container_width=True)
