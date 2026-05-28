# Databricks notebook source
# MAGIC %md
# MAGIC # 04 — Analytics & Visualisation
# MAGIC EDA charts: revenue over time, top products, user segments, payment methods.

# COMMAND ----------
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

DELTA_BASE = "dbfs:/FileStore/ecommerce/delta/"
OUT_PATH   = "/dbfs/FileStore/ecommerce/outputs/charts/"

import os; os.makedirs(OUT_PATH, exist_ok=True)

df_orders   = spark.read.format("delta").load(DELTA_BASE + "orders_clean")
df_monthly  = spark.read.format("delta").load(DELTA_BASE + "features_monthly")
df_category = spark.read.format("delta").load(DELTA_BASE + "features_category")

# COMMAND ----------
# MAGIC %md ## 1 — Monthly Revenue Trend

pdf_monthly = df_monthly.orderBy("year", "month").toPandas()
pdf_monthly["period"] = pdf_monthly["year"].astype(str) + "-" + pdf_monthly["month"].astype(str).str.zfill(2)

fig, ax = plt.subplots(figsize=(14, 5))
ax.fill_between(pdf_monthly["period"], pdf_monthly["revenue"], alpha=0.2, color="#1D9E75")
ax.plot(pdf_monthly["period"], pdf_monthly["revenue"], color="#1D9E75", linewidth=2)
ax.set_title("Monthly Revenue", fontsize=14, fontweight="bold")
ax.set_xlabel("Month")
ax.set_ylabel("Revenue (USD)")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
plt.xticks(rotation=45, ha="right", fontsize=8)
plt.tight_layout()
plt.savefig(OUT_PATH + "01_monthly_revenue.png", dpi=150)
plt.show()
print("Saved: 01_monthly_revenue.png")

# COMMAND ----------
# MAGIC %md ## 2 — Revenue by Category

pdf_cat = df_category.toPandas().sort_values("revenue", ascending=True)

fig, ax = plt.subplots(figsize=(10, 6))
bars = ax.barh(pdf_cat["category"], pdf_cat["revenue"], color="#7F77DD", edgecolor="none")
ax.bar_label(bars, labels=[f"${v:,.0f}" for v in pdf_cat["revenue"]], padding=6, fontsize=9)
ax.set_title("Revenue by Product Category", fontsize=14, fontweight="bold")
ax.set_xlabel("Revenue (USD)")
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
plt.tight_layout()
plt.savefig(OUT_PATH + "02_revenue_by_category.png", dpi=150)
plt.show()

# COMMAND ----------
# MAGIC %md ## 3 — Order Status Distribution

pdf_status = df_orders.groupBy("status").count().toPandas()
colors = {"delivered": "#1D9E75", "shipped": "#7F77DD", "confirmed": "#EF9F27",
          "pending": "#888780", "cancelled": "#E24B4A"}

fig, ax = plt.subplots(figsize=(8, 8))
wedges, texts, autotexts = ax.pie(
    pdf_status["count"],
    labels=pdf_status["status"],
    autopct="%1.1f%%",
    colors=[colors.get(s, "#888780") for s in pdf_status["status"]],
    startangle=140,
    pctdistance=0.82,
)
for t in autotexts: t.set_fontsize(10)
ax.set_title("Order Status Distribution", fontsize=14, fontweight="bold")
plt.tight_layout()
plt.savefig(OUT_PATH + "03_order_status.png", dpi=150)
plt.show()

# COMMAND ----------
# MAGIC %md ## 4 — Orders by Day of Week

from pyspark.sql.functions import count
day_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

pdf_dow = df_orders.groupBy("day_of_week").count().toPandas()
pdf_dow["day_of_week"] = pd.Categorical(pdf_dow["day_of_week"], categories=day_order, ordered=True)
pdf_dow = pdf_dow.sort_values("day_of_week")

fig, ax = plt.subplots(figsize=(10, 5))
ax.bar(pdf_dow["day_of_week"], pdf_dow["count"], color="#5DCAA5", edgecolor="none")
ax.set_title("Orders by Day of Week", fontsize=14, fontweight="bold")
ax.set_ylabel("Number of Orders")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
plt.tight_layout()
plt.savefig(OUT_PATH + "04_orders_by_dow.png", dpi=150)
plt.show()

# COMMAND ----------
# MAGIC %md ## 5 — Revenue by User Segment

pdf_seg = df_orders.groupBy("user_segment").agg(
    F.count("order_id").alias("orders"),
    F.round(F.sum("total_amount"), 2).alias("revenue"),
).toPandas()

fig, axes = plt.subplots(1, 2, figsize=(12, 5))
colors_seg = ["#7F77DD", "#1D9E75", "#EF9F27", "#E24B4A"]
axes[0].bar(pdf_seg["user_segment"], pdf_seg["orders"], color=colors_seg, edgecolor="none")
axes[0].set_title("Orders by Segment")
axes[1].bar(pdf_seg["user_segment"], pdf_seg["revenue"], color=colors_seg, edgecolor="none")
axes[1].set_title("Revenue by Segment")
axes[1].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
for ax in axes: ax.set_xlabel("Segment")
plt.tight_layout()
plt.savefig(OUT_PATH + "05_segment_analysis.png", dpi=150)
plt.show()

# COMMAND ----------
# MAGIC %md ## 6 — Payment Method Distribution

pdf_pay = df_orders.groupBy("payment_method").count().orderBy("count", ascending=False).toPandas()

fig, ax = plt.subplots(figsize=(9, 5))
ax.bar(pdf_pay["payment_method"], pdf_pay["count"], color="#D85A30", edgecolor="none")
ax.set_title("Orders by Payment Method", fontsize=14, fontweight="bold")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
plt.tight_layout()
plt.savefig(OUT_PATH + "06_payment_methods.png", dpi=150)
plt.show()

print(f"\nAll charts saved to {OUT_PATH}")
