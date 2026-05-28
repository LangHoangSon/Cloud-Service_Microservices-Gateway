# Databricks notebook source
# MAGIC %md
# MAGIC # 01 — Data Loading
# MAGIC Load raw JSON files from DBFS into Delta Lake tables.

# COMMAND ----------
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, input_file_name
from pyspark.sql.types import *

spark = SparkSession.builder.appName("EcommerceDataLoading").getOrCreate()

# COMMAND ----------
# MAGIC %md ## Config — DBFS paths

RAW_ORDERS_PATH  = "dbfs:/FileStore/ecommerce/raw/orders/"
RAW_USERS_PATH   = "dbfs:/FileStore/ecommerce/raw/users/users.json"
DELTA_BASE       = "dbfs:/FileStore/ecommerce/delta/"

# COMMAND ----------
# MAGIC %md ## Load Orders

order_item_schema = ArrayType(StructType([
    StructField("product_id",   StringType()),
    StructField("product_name", StringType()),
    StructField("category",     StringType()),
    StructField("quantity",     IntegerType()),
    StructField("unit_price",   DoubleType()),
]))

orders_schema = StructType([
    StructField("order_id",       StringType(),  True),
    StructField("user_id",        StringType(),  True),
    StructField("user_segment",   StringType(),  True),
    StructField("user_city",      StringType(),  True),
    StructField("status",         StringType(),  True),
    StructField("total_amount",   DoubleType(),  True),
    StructField("item_count",     IntegerType(), True),
    StructField("payment_method", StringType(),  True),
    StructField("year",           IntegerType(), True),
    StructField("month",          IntegerType(), True),
    StructField("day_of_week",    StringType(),  True),
    StructField("created_at",     StringType(),  True),
    StructField("updated_at",     StringType(),  True),
    StructField("items",          order_item_schema, True),
])

df_orders = spark.read.schema(orders_schema).json(RAW_ORDERS_PATH)

print(f"Orders loaded: {df_orders.count():,}")
df_orders.printSchema()
df_orders.show(5, truncate=True)

# COMMAND ----------
# MAGIC %md ## Load Users

users_schema = StructType([
    StructField("user_id",       StringType(), True),
    StructField("username",      StringType(), True),
    StructField("email",         StringType(), True),
    StructField("full_name",     StringType(), True),
    StructField("city",          StringType(), True),
    StructField("segment",       StringType(), True),
    StructField("age",           IntegerType(), True),
    StructField("registered_at", StringType(), True),
])

df_users = spark.read.schema(users_schema).json(RAW_USERS_PATH)

print(f"Users loaded: {df_users.count():,}")
df_users.show(5)

# COMMAND ----------
# MAGIC %md ## Save to Delta Lake

df_orders.write.format("delta").mode("overwrite").save(DELTA_BASE + "orders_raw")
df_users.write.format("delta").mode("overwrite").save(DELTA_BASE + "users_raw")

print("Delta tables saved:")
print(f"  {DELTA_BASE}orders_raw")
print(f"  {DELTA_BASE}users_raw")

# COMMAND ----------
# Quick sanity check
spark.read.format("delta").load(DELTA_BASE + "orders_raw").groupBy("status").count().show()
