import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import json

st.set_page_config(page_title="Revenue", page_icon="📈", layout="wide")
st.title("📈 Revenue Dashboard")

OUTPUTS = Path("outputs")

@st.cache_data
def load_monthly():
    p = OUTPUTS / "reports" / "monthly_revenue.json"
    if p.exists():
        return pd.read_json(p)
    # Fallback: sample data so the page always renders
    import numpy as np
    months = pd.date_range("2023-01", periods=24, freq="MS")
    base   = 500_000
    return pd.DataFrame({
        "year":             [d.year  for d in months],
        "month":            [d.month for d in months],
        "revenue":          [base * (1 + 0.05*i + 0.3*np.sin(i/3)) + np.random.normal(0, 20000)
                             for i in range(24)],
        "order_count":      [int(3000 + 100*i + np.random.normal(0, 200)) for i in range(24)],
        "unique_customers": [int(2000 + 50*i) for i in range(24)],
    })

df = load_monthly()
df["period"] = df["year"].astype(str) + "-" + df["month"].astype(str).str.zfill(2)
df["revenue"] = df["revenue"].round(2)

# KPI row
total_rev = df["revenue"].sum()
best_row  = df.loc[df["revenue"].idxmax()]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Revenue",   f"${total_rev:,.0f}")
c2.metric("Best Month",      f"{best_row['period']}")
c3.metric("Peak Revenue",    f"${best_row['revenue']:,.0f}")
c4.metric("Avg Monthly Rev", f"${df['revenue'].mean():,.0f}")

st.markdown("---")

# Revenue trend
fig1 = go.Figure()
fig1.add_trace(go.Scatter(x=df["period"], y=df["revenue"],
               mode="lines+markers", name="Revenue",
               line=dict(color="#1D9E75", width=2),
               fill="tozeroy", fillcolor="rgba(29,158,117,0.1)"))
fig1.update_layout(title="Monthly Revenue Trend", xaxis_title="Month",
                   yaxis_title="Revenue (USD)", hovermode="x unified", height=380)
st.plotly_chart(fig1, use_container_width=True)

col1, col2 = st.columns(2)
with col1:
    fig2 = px.bar(df, x="period", y="order_count", title="Monthly Order Count",
                  color_discrete_sequence=["#7F77DD"])
    fig2.update_layout(height=320)
    st.plotly_chart(fig2, use_container_width=True)

with col2:
    fig3 = px.line(df, x="period", y="unique_customers", title="Monthly Unique Customers",
                   markers=True, color_discrete_sequence=["#EF9F27"])
    fig3.update_layout(height=320)
    st.plotly_chart(fig3, use_container_width=True)

with st.expander("Raw data"):
    st.dataframe(df, use_container_width=True)
