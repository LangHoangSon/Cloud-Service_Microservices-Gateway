# Databricks notebook source
# MAGIC %md
# MAGIC # 02 — Data Cleaning
# MAGIC Validate, deduplicate, fix types, remove nulls.

# COMMAND ----------

# RAW_ORDERS_PATH  = "/Volumes/workspace/default/data_cloud_500k/orders/"
# RAW_USERS_PATH   = "/Volumes/workspace/default/data_cloud_500k/users/users.json"
# DELTA_BASE       = "/Volumes/workspace/default/data_cloud_500k/delta/"
from pyspark.sql import functions as F
from pyspark.sql.functions import col, to_timestamp, when, count, isnan, isnull

DELTA_BASE = "dbfs:/FileStore/ecommerce/delta/"

df_orders = spark.read.format("delta").load(DELTA_BASE + "orders_raw")
df_users  = spark.read.format("delta").load(DELTA_BASE + "users_raw")

print(f"Raw orders: {df_orders.count():,}")
print(f"Raw users:  {df_users.count():,}")

# COMMAND ----------
# MAGIC %md ## Null check

def null_report(df, name):
    print(f"\n── {name} null counts ──")
    for c in df.columns:
        n = df.filter(col(c).isNull() | (col(c) == "")).count()
        if n > 0:
            print(f"  {c}: {n:,}")

null_report(df_orders, "orders")
null_report(df_users,  "users")

# COMMAND ----------
# MAGIC %md ## Clean Orders

df_orders_clean = (
    df_orders
    # Drop rows missing critical fields
    .dropna(subset=["order_id", "user_id", "status", "total_amount", "created_at"])

    # Deduplicate on order_id (keep first occurrence)
    .dropDuplicates(["order_id"])

    # Cast timestamps
    .withColumn("created_at", to_timestamp(col("created_at")))
    .withColumn("updated_at", to_timestamp(col("updated_at")))

    # Remove impossible values
    .filter(col("total_amount") > 0)
    .filter(col("item_count")   > 0)

    # Standardise status to lowercase
    .withColumn("status", F.lower(col("status")))

    # Add date partition columns
    .withColumn("order_date", F.to_date(col("created_at")))
    .withColumn("hour",       F.hour(col("created_at")))
)

print(f"Clean orders: {df_orders_clean.count():,}")

# COMMAND ----------
# MAGIC %md ## Clean Users

df_users_clean = (
    df_users
    .dropna(subset=["user_id", "email"])
    .dropDuplicates(["user_id"])
    .withColumn("registered_at", to_timestamp(col("registered_at")))
)

print(f"Clean users: {df_users_clean.count():,}")

# COMMAND ----------
# MAGIC %md ## Save cleaned Delta tables

df_orders_clean.write.format("delta").mode("overwrite").save(DELTA_BASE + "orders_clean")
df_users_clean.write.format("delta").mode("overwrite").save(DELTA_BASE + "users_clean")

print("Saved: orders_clean, users_clean")

# Summary stats
df_orders_clean.groupBy("status").agg(
    count("*").alias("count"),
    F.round(F.avg("total_amount"), 2).alias("avg_amount"),
    F.round(F.sum("total_amount"), 2).alias("total_revenue"),
).orderBy("count", ascending=False).show()
