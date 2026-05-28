# Databricks notebook source
# MAGIC %md
# MAGIC # 06 — Insight Generation
# MAGIC Auto-generate business insights from cluster profiles and revenue forecast.

# COMMAND ----------
import json
from datetime import datetime
from pyspark.sql import functions as F

DELTA_BASE = "dbfs:/FileStore/ecommerce/delta/"
OUT_PATH   = "/dbfs/FileStore/ecommerce/outputs/"

df_orders   = spark.read.format("delta").load(DELTA_BASE + "orders_clean")
df_clusters = spark.read.format("delta").load(DELTA_BASE + "cluster_profiles")
df_monthly  = spark.read.format("delta").load(DELTA_BASE + "features_monthly")
df_category = spark.read.format("delta").load(DELTA_BASE + "features_category")

# COMMAND ----------
# MAGIC %md ## Overall KPIs

kpis = df_orders.agg(
    F.count("order_id").alias("total_orders"),
    F.round(F.sum("total_amount"), 2).alias("total_revenue"),
    F.round(F.avg("total_amount"), 2).alias("avg_order_value"),
    F.countDistinct("user_id").alias("unique_customers"),
).collect()[0]

delivered_rate = (
    df_orders.filter(F.col("status") == "delivered").count()
    / df_orders.count() * 100
)
cancelled_rate = (
    df_orders.filter(F.col("status") == "cancelled").count()
    / df_orders.count() * 100
)

print("=" * 50)
print("OVERALL KPIs")
print("=" * 50)
print(f"Total orders:       {kpis['total_orders']:,}")
print(f"Total revenue:      ${kpis['total_revenue']:,.2f}")
print(f"Avg order value:    ${kpis['avg_order_value']:,.2f}")
print(f"Unique customers:   {kpis['unique_customers']:,}")
print(f"Delivery rate:      {delivered_rate:.1f}%")
print(f"Cancellation rate:  {cancelled_rate:.1f}%")

# COMMAND ----------
# MAGIC %md ## Cluster Insights

pdf_clusters = df_clusters.orderBy("avg_spend", ascending=False).toPandas()

SEGMENT_LABELS = {0: "Champions", 1: "Loyal Customers", 2: "At-Risk",
                  3: "New Customers", 4: "Occasional"}

cluster_insights = []
for _, row in pdf_clusters.iterrows():
    cid   = int(row["prediction"])
    label = SEGMENT_LABELS.get(cid, f"Segment {cid}")

    if row["avg_recency"] < 30:
        recency_desc = "very recently active"
    elif row["avg_recency"] < 90:
        recency_desc = "moderately recent"
    else:
        recency_desc = "have not ordered recently"

    insight = (
        f"Segment {cid} — {label}: {int(row['users']):,} customers who {recency_desc}, "
        f"averaging {row['avg_frequency']:.1f} orders and ${row['avg_spend']:,.0f} total spend. "
        f"Avg order value: ${row['avg_order_val']:,.2f}."
    )

    if row["avg_spend"] == pdf_clusters["avg_spend"].max():
        insight += " → High-value segment: prioritise retention campaigns."
    elif row["avg_recency"] == pdf_clusters["avg_recency"].max():
        insight += " → Dormant segment: consider win-back promotions."
    elif row["avg_frequency"] == pdf_clusters["avg_frequency"].max():
        insight += " → Most frequent buyers: good candidates for loyalty rewards."

    cluster_insights.append(insight)
    print(insight)
    print()

# COMMAND ----------
# MAGIC %md ## Revenue Trend Insights

pdf_monthly = df_monthly.orderBy("year", "month").toPandas()

best_month  = pdf_monthly.loc[pdf_monthly["revenue"].idxmax()]
worst_month = pdf_monthly.loc[pdf_monthly["revenue"].idxmin()]
last_3      = pdf_monthly.tail(3)
growth_3m   = ((last_3.iloc[-1]["revenue"] - last_3.iloc[0]["revenue"])
               / last_3.iloc[0]["revenue"] * 100)

revenue_insights = [
    f"Peak revenue month: {int(best_month['year'])}-{int(best_month['month']):02d} "
    f"(${best_month['revenue']:,.0f}) — likely driven by seasonal promotions.",

    f"Lowest revenue month: {int(worst_month['year'])}-{int(worst_month['month']):02d} "
    f"(${worst_month['revenue']:,.0f}).",

    f"3-month revenue trend: {growth_3m:+.1f}% — "
    + ("positive growth momentum." if growth_3m > 0 else "declining, investigate causes."),
]

for r in revenue_insights:
    print(r)

# COMMAND ----------
# MAGIC %md ## Category Insights

pdf_cat = df_category.orderBy("revenue", ascending=False).toPandas()
top_cat    = pdf_cat.iloc[0]
bottom_cat = pdf_cat.iloc[-1]

category_insights = [
    f"Top category: {top_cat['category']} (${top_cat['revenue']:,.0f} revenue, "
    f"{int(top_cat['order_count']):,} orders).",

    f"Lowest revenue category: {bottom_cat['category']} (${bottom_cat['revenue']:,.0f}) "
    f"— consider bundling or promotional pricing.",
]

for c in category_insights:
    print(c)

# COMMAND ----------
# MAGIC %md ## Save Insights Report

report = {
    "generated_at": datetime.now().isoformat(),
    "kpis": {
        "total_orders":     int(kpis["total_orders"]),
        "total_revenue":    float(kpis["total_revenue"]),
        "avg_order_value":  float(kpis["avg_order_value"]),
        "unique_customers": int(kpis["unique_customers"]),
        "delivery_rate_pct":    round(delivered_rate, 1),
        "cancellation_rate_pct": round(cancelled_rate, 1),
    },
    "cluster_insights":  cluster_insights,
    "revenue_insights":  revenue_insights,
    "category_insights": category_insights,
}

import os; os.makedirs(OUT_PATH + "summaries/", exist_ok=True)
with open(OUT_PATH + "summaries/insights_report.json", "w") as f:
    json.dump(report, f, indent=2)

print(f"\nInsights report saved → {OUT_PATH}summaries/insights_report.json")
