# Databricks notebook source
# MAGIC %md
# MAGIC # 03 — Feature Engineering
# MAGIC Build RFM (Recency, Frequency, Monetary) features per user.
# MAGIC These features feed directly into KMeans clustering (notebook 05).

# COMMAND ----------
from pyspark.sql import functions as F
from pyspark.sql.functions import col, datediff, current_date, count, sum, avg, max, min, stddev
from pyspark.sql.window import Window

DELTA_BASE = "dbfs:/FileStore/ecommerce/delta/"

df_orders = spark.read.format("delta").load(DELTA_BASE + "orders_clean")
df_users  = spark.read.format("delta").load(DELTA_BASE + "users_clean")

# Use only completed orders for RFM
df_completed = df_orders.filter(col("status").isin(["delivered", "confirmed", "shipped"]))
print(f"Completed orders for features: {df_completed.count():,}")

# COMMAND ----------
# MAGIC %md ## RFM Features (per user)

df_rfm = df_completed.groupBy("user_id").agg(
    # Recency: days since last order (lower = more recent = better)
    datediff(current_date(), max("created_at")).alias("recency_days"),

    # Frequency: number of orders
    count("order_id").alias("frequency"),

    # Monetary: total spend
    F.round(sum("total_amount"), 2).alias("monetary_total"),

    # Extra features
    F.round(avg("total_amount"), 2).alias("avg_order_value"),
    F.round(avg("item_count"),   2).alias("avg_items_per_order"),
    max("total_amount").alias("max_order_value"),
)

print("RFM sample:")
df_rfm.show(10)

# COMMAND ----------
# MAGIC %md ## Time-based Features (per order)

df_time_features = df_orders.select(
    "order_id",
    "user_id",
    "total_amount",
    "status",
    "user_segment",
    "user_city",
    "payment_method",
    col("year"),
    col("month"),
    col("day_of_week"),
    F.hour("created_at").alias("hour_of_day"),
    F.dayofmonth("created_at").alias("day_of_month"),
    F.quarter("created_at").alias("quarter"),
    # Weekend flag
    F.when(col("day_of_week").isin(["Saturday", "Sunday"]), 1).otherwise(0).alias("is_weekend"),
    # Business hours flag
    F.when((F.hour("created_at") >= 9) & (F.hour("created_at") <= 18), 1).otherwise(0).alias("is_business_hours"),
)

# COMMAND ----------
# MAGIC %md ## Monthly revenue aggregation (for forecasting)

df_monthly = df_completed.groupBy("year", "month").agg(
    count("order_id").alias("order_count"),
    F.round(sum("total_amount"), 2).alias("revenue"),
    F.round(avg("total_amount"), 2).alias("avg_order_value"),
    F.countDistinct("user_id").alias("unique_customers"),
).orderBy("year", "month")

print("Monthly revenue:")
df_monthly.show(24)

# COMMAND ----------
# MAGIC %md ## Category revenue (for product analytics)

from pyspark.sql.functions import explode

df_items = df_orders.select("order_id", "user_id", "created_at", "status",
                             explode("items").alias("item"))

df_category = df_items.filter(col("status").isin(["delivered", "confirmed", "shipped"])).select(
    "order_id",
    col("item.product_id").alias("product_id"),
    col("item.product_name").alias("product_name"),
    col("item.category").alias("category"),
    col("item.quantity").alias("quantity"),
    col("item.unit_price").alias("unit_price"),
    F.round(col("item.quantity") * col("item.unit_price"), 2).alias("line_total"),
)

df_category_summary = df_category.groupBy("category").agg(
    count("order_id").alias("order_count"),
    F.round(sum("line_total"), 2).alias("revenue"),
    F.round(avg("unit_price"),  2).alias("avg_price"),
).orderBy("revenue", ascending=False)

print("Revenue by category:")
df_category_summary.show()

# COMMAND ----------
# MAGIC %md ## Save feature tables

df_rfm.write.format("delta").mode("overwrite").save(DELTA_BASE + "features_rfm")
df_time_features.write.format("delta").mode("overwrite").save(DELTA_BASE + "features_time")
df_monthly.write.format("delta").mode("overwrite").save(DELTA_BASE + "features_monthly")
df_category_summary.write.format("delta").mode("overwrite").save(DELTA_BASE + "features_category")

print("Feature tables saved: features_rfm, features_time, features_monthly, features_category")
