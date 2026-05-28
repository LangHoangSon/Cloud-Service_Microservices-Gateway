import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="Product Analytics", page_icon="📦", layout="wide")
st.title("📦 Product Analytics")

OUTPUTS = Path("outputs")

@st.cache_data
def load_categories():
    p = OUTPUTS / "reports" / "category_summary.json"
    if p.exists():
        return pd.read_json(p)
    return pd.DataFrame({
        "category":    ["Electronics","Furniture","Books","Appliances","Stationery"],
        "revenue":     [3_200_000, 1_800_000, 950_000, 1_100_000, 420_000],
        "order_count": [42000, 18000, 32000, 24000, 51000],
        "avg_price":   [289, 224, 43, 91, 19],
    })

df = load_categories()

c1, c2, c3 = st.columns(3)
c1.metric("Top Category",      df.loc[df["revenue"].idxmax(), "category"])
c2.metric("Top Revenue",       f"${df['revenue'].max():,.0f}")
c3.metric("Total SKU Orders",  f"{df['order_count'].sum():,}")

st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    fig1 = px.bar(df.sort_values("revenue"), x="revenue", y="category",
                  orientation="h", title="Revenue by Category",
                  color="revenue", color_continuous_scale="Teal")
    fig1.update_layout(coloraxis_showscale=False, height=340)
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    fig2 = px.scatter(df, x="avg_price", y="order_count",
                      size="revenue", color="category", text="category",
                      title="Avg Price vs Order Volume",
                      size_max=55)
    fig2.update_traces(textposition="top center")
    fig2.update_layout(height=340)
    st.plotly_chart(fig2, use_container_width=True)

fig3 = px.pie(df, names="category", values="order_count",
              title="Order Share by Category",
              color_discrete_sequence=px.colors.qualitative.Set2)
st.plotly_chart(fig3, use_container_width=True)

with st.expander("Data table"):
    st.dataframe(df, use_container_width=True)
