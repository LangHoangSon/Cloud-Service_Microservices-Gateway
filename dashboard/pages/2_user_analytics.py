import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import json

st.set_page_config(page_title="User Analytics", page_icon="👥", layout="wide")
st.title("👥 Customer Segmentation")
st.markdown("KMeans clustering on RFM (Recency, Frequency, Monetary) features.")

OUTPUTS = Path("outputs")

@st.cache_data
def load_clusters():
    p = OUTPUTS / "reports" / "cluster_profiles.json"
    if p.exists():
        return pd.read_json(p)
    # Fallback sample
    return pd.DataFrame({
        "prediction":    [0, 1, 2, 3],
        "users":         [12400, 38200, 31500, 18100],
        "avg_recency":   [18,    45,    120,   8],
        "avg_frequency": [12.4,  6.2,   1.8,   1.1],
        "avg_spend":     [4820,  1950,  480,   210],
        "avg_order_val": [389,   314,   267,   191],
    })

df = load_clusters()
LABELS = {0: "Champions", 1: "Loyal", 2: "At-Risk", 3: "New"}
df["segment"] = df["prediction"].map(LABELS).fillna("Segment " + df["prediction"].astype(str))

# KPI row
c1, c2, c3 = st.columns(3)
c1.metric("Total Segments",      len(df))
c2.metric("Highest Avg Spend",   f"${df['avg_spend'].max():,.0f}")
c3.metric("Total Users Analysed", f"{df['users'].sum():,}")

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    fig1 = px.pie(df, names="segment", values="users",
                  title="User Distribution by Segment",
                  color_discrete_sequence=["#1D9E75","#7F77DD","#EF9F27","#E24B4A"])
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    fig2 = px.bar(df, x="segment", y="avg_spend",
                  title="Avg Total Spend per Segment",
                  color="segment",
                  color_discrete_sequence=["#1D9E75","#7F77DD","#EF9F27","#E24B4A"])
    st.plotly_chart(fig2, use_container_width=True)

# RFM scatter
st.subheader("RFM Scatter — Frequency vs Spend (bubble = user count)")
fig3 = px.scatter(df, x="avg_recency", y="avg_spend",
                  size="users", color="segment", text="segment",
                  size_max=60, title="Recency vs Monetary Value",
                  labels={"avg_recency": "Avg Recency (days)", "avg_spend": "Avg Total Spend ($)"},
                  color_discrete_sequence=["#1D9E75","#7F77DD","#EF9F27","#E24B4A"])
fig3.update_traces(textposition="top center")
fig3.update_layout(height=420)
st.plotly_chart(fig3, use_container_width=True)

st.subheader("Segment Profiles")
st.dataframe(df.rename(columns={
    "prediction": "Cluster ID", "users": "Users",
    "avg_recency": "Avg Recency (days)", "avg_frequency": "Avg Frequency",
    "avg_spend": "Avg Total Spend ($)", "avg_order_val": "Avg Order Value ($)",
    "segment": "Segment",
}), use_container_width=True)
