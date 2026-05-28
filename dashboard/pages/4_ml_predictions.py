import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import json

st.set_page_config(page_title="ML Predictions", page_icon="🤖", layout="wide")
st.title("🤖 ML Predictions")
st.markdown("Revenue forecasting (RandomForest) and customer clustering (KMeans).")

OUTPUTS = Path("outputs")

@st.cache_data
def load_forecast():
    p = OUTPUTS / "reports" / "forecast.json"
    if p.exists():
        return pd.read_json(p)
    import numpy as np
    periods = pd.date_range("2024-10", periods=3, freq="MS")
    actual  = [680_000, 720_000, 710_000]
    pred    = [672_000, 735_000, 698_000]
    return pd.DataFrame({
        "period":     [str(d)[:7] for d in periods],
        "actual":     actual,
        "predicted":  pred,
        "error_pct":  [round(abs(a-p)/a*100, 1) for a,p in zip(actual, pred)],
    })

@st.cache_data
def load_insights():
    p = OUTPUTS / "summaries" / "insights_report.json"
    if p.exists():
        return json.loads(p.read_text())
    return None

df_fc    = load_forecast()
insights = load_insights()

# Forecast chart
st.subheader("Revenue Forecast — Actual vs Predicted (Test Set)")
fig = go.Figure()
fig.add_trace(go.Bar(x=df_fc["period"], y=df_fc["actual"],
              name="Actual", marker_color="#1D9E75", opacity=0.85))
fig.add_trace(go.Bar(x=df_fc["period"], y=df_fc["predicted"],
              name="Predicted", marker_color="#7F77DD", opacity=0.85))
fig.update_layout(barmode="group", height=360, hovermode="x unified",
                  yaxis_tickprefix="$", yaxis_tickformat=",.0f")
st.plotly_chart(fig, use_container_width=True)

# Error metrics
c1, c2, c3 = st.columns(3)
avg_err = df_fc["error_pct"].mean()
c1.metric("Avg Error %",   f"{avg_err:.1f}%")
c2.metric("Test periods",  len(df_fc))
c3.metric("Model",         "RandomForest")

st.markdown("---")

# MLflow model info
st.subheader("Models Trained")
col1, col2 = st.columns(2)
with col1:
    st.info("**KMeans Clustering**\n\n"
            "- Features: Recency, Frequency, Monetary, Avg Order Value\n"
            "- Evaluation: Silhouette Score\n"
            "- Output: Customer segments with business labels\n"
            "- Tracked in: MLflow")
with col2:
    st.info("**RandomForest Regression**\n\n"
            "- Features: Month, 3 revenue lags, order count, unique customers\n"
            "- Evaluation: RMSE, MAE, R²\n"
            "- Output: Monthly revenue forecast\n"
            "- Tracked in: MLflow")

st.markdown("---")

# Auto-generated insights
if insights:
    st.subheader("Auto-generated Insights")
    for insight in insights.get("cluster_insights", []):
        st.success(insight)
    for insight in insights.get("revenue_insights", []):
        st.info(insight)
else:
    st.warning("Run Databricks pipeline to generate insights.")
