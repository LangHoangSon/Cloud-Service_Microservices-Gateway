# Databricks notebook source
# MAGIC %md
# MAGIC # 05 — ML Training
# MAGIC Model 1: KMeans customer segmentation (RFM features)
# MAGIC Model 2: Linear Regression revenue forecasting (monthly data)
# MAGIC Both tracked with MLflow.

# COMMAND ----------
import mlflow
import mlflow.spark
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.clustering import KMeans
from pyspark.ml.regression import LinearRegression, RandomForestRegressor
from pyspark.ml.evaluation import ClusteringEvaluator, RegressionEvaluator
from pyspark.ml import Pipeline
from pyspark.sql import functions as F

DELTA_BASE  = "dbfs:/FileStore/ecommerce/delta/"
OUT_PATH    = "/dbfs/FileStore/ecommerce/outputs/"
MODEL_PATH  = "dbfs:/FileStore/ecommerce/models/"

import os
os.makedirs(OUT_PATH + "charts/", exist_ok=True)

df_rfm     = spark.read.format("delta").load(DELTA_BASE + "features_rfm")
df_monthly = spark.read.format("delta").load(DELTA_BASE + "features_monthly")

# COMMAND ----------
# MAGIC %md ## Model 1 — KMeans Customer Segmentation

# COMMAND ----------
# Drop nulls, fill edge cases
df_rfm_clean = df_rfm.dropna().filter(F.col("frequency") > 0)

rfm_features = ["recency_days", "frequency", "monetary_total", "avg_order_value"]
assembler  = VectorAssembler(inputCols=rfm_features, outputCol="raw_features")
scaler     = StandardScaler(inputCol="raw_features", outputCol="features", withMean=True, withStd=True)

# Elbow method — find optimal K
print("Running elbow method (K=2..8)...")
silhouette_scores = {}
evaluator = ClusteringEvaluator(featuresCol="features", metricName="silhouette")

with mlflow.start_run(run_name="KMeans_elbow"):
    for k in range(2, 9):
        kmeans    = KMeans(k=k, seed=42, featuresCol="features")
        pipeline  = Pipeline(stages=[assembler, scaler, kmeans])
        model     = pipeline.fit(df_rfm_clean)
        preds     = model.transform(df_rfm_clean)
        score     = evaluator.evaluate(preds)
        silhouette_scores[k] = score
        mlflow.log_metric(f"silhouette_k{k}", score)
        print(f"  K={k}  silhouette={score:.4f}")

# Pick best K
best_k = max(silhouette_scores, key=silhouette_scores.get)
print(f"\nBest K = {best_k}  (silhouette={silhouette_scores[best_k]:.4f})")

# Plot elbow
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(list(silhouette_scores.keys()), list(silhouette_scores.values()),
        marker="o", color="#7F77DD", linewidth=2)
ax.axvline(x=best_k, color="#E24B4A", linestyle="--", label=f"Best K={best_k}")
ax.set_title("KMeans Elbow — Silhouette Score", fontsize=13, fontweight="bold")
ax.set_xlabel("K"); ax.set_ylabel("Silhouette Score"); ax.legend()
plt.tight_layout()
plt.savefig(OUT_PATH + "charts/ml_elbow.png", dpi=150)
plt.show()

# COMMAND ----------
# Train final KMeans with best_k
with mlflow.start_run(run_name=f"KMeans_K{best_k}_final"):
    mlflow.log_param("k", best_k)
    mlflow.log_param("features", rfm_features)

    kmeans_final = KMeans(k=best_k, seed=42, featuresCol="features")
    pipeline_final = Pipeline(stages=[assembler, scaler, kmeans_final])
    model_km = pipeline_final.fit(df_rfm_clean)

    df_clustered = model_km.transform(df_rfm_clean)

    final_score = evaluator.evaluate(df_clustered)
    mlflow.log_metric("silhouette", final_score)
    print(f"Final silhouette score: {final_score:.4f}")

    # Save model
    model_km.write().overwrite().save(MODEL_PATH + "kmeans_final")
    mlflow.log_artifact(OUT_PATH + "charts/ml_elbow.png")

# Cluster profile
cluster_profile = df_clustered.groupBy("prediction").agg(
    F.count("user_id").alias("users"),
    F.round(F.avg("recency_days"),    1).alias("avg_recency"),
    F.round(F.avg("frequency"),       1).alias("avg_frequency"),
    F.round(F.avg("monetary_total"),  2).alias("avg_spend"),
    F.round(F.avg("avg_order_value"), 2).alias("avg_order_val"),
).orderBy("avg_spend", ascending=False)

print("\nCluster profiles:")
cluster_profile.show()
cluster_profile.write.format("delta").mode("overwrite").save(DELTA_BASE + "cluster_profiles")

# COMMAND ----------
# MAGIC %md ## Model 2 — Monthly Revenue Forecasting

# COMMAND ----------
# Add lag features for time-series regression
from pyspark.sql.window import Window

w = Window.orderBy("year", "month")
df_ts = df_monthly.withColumn("revenue_lag1", F.lag("revenue", 1).over(w)) \
                  .withColumn("revenue_lag2", F.lag("revenue", 2).over(w)) \
                  .withColumn("revenue_lag3", F.lag("revenue", 3).over(w)) \
                  .dropna()

ts_features = ["month", "revenue_lag1", "revenue_lag2", "revenue_lag3",
               "order_count", "unique_customers"]

assembler_ts = VectorAssembler(inputCols=ts_features, outputCol="features")

# Train/test split (last 3 months = test)
n = df_ts.count()
df_train = df_ts.limit(n - 3)
df_test  = df_ts.subtract(df_train)

print(f"Train rows: {df_train.count()}, Test rows: {df_test.count()}")

# COMMAND ----------
reg_evaluator = RegressionEvaluator(labelCol="revenue", predictionCol="prediction",
                                     metricName="rmse")

with mlflow.start_run(run_name="Revenue_RandomForest"):
    mlflow.log_param("model", "RandomForestRegressor")
    mlflow.log_param("features", ts_features)

    rf = RandomForestRegressor(labelCol="revenue", featuresCol="features",
                               numTrees=50, maxDepth=5, seed=42)
    pipeline_rf = Pipeline(stages=[assembler_ts, rf])
    model_rf = pipeline_rf.fit(df_train)

    preds_rf = model_rf.transform(df_test)
    rmse = reg_evaluator.evaluate(preds_rf)
    mae  = RegressionEvaluator(labelCol="revenue", predictionCol="prediction",
                                metricName="mae").evaluate(preds_rf)
    r2   = RegressionEvaluator(labelCol="revenue", predictionCol="prediction",
                                metricName="r2").evaluate(preds_rf)

    mlflow.log_metric("rmse", rmse)
    mlflow.log_metric("mae",  mae)
    mlflow.log_metric("r2",   r2)

    print(f"RandomForest → RMSE: ${rmse:,.0f}  MAE: ${mae:,.0f}  R²: {r2:.4f}")

    model_rf.write().overwrite().save(MODEL_PATH + "revenue_rf")

# COMMAND ----------
# Visualise actual vs predicted
pdf_preds = preds_rf.select("year", "month", "revenue", "prediction").toPandas()
pdf_preds["period"] = pdf_preds["year"].astype(str) + "-" + pdf_preds["month"].astype(str).str.zfill(2)

fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(pdf_preds["period"], pdf_preds["revenue"],    marker="o", label="Actual",    color="#1D9E75")
ax.plot(pdf_preds["period"], pdf_preds["prediction"], marker="s", label="Predicted", color="#7F77DD", linestyle="--")
ax.set_title("Revenue — Actual vs Predicted (test set)", fontsize=13, fontweight="bold")
ax.set_ylabel("Revenue (USD)")
ax.legend(); plt.tight_layout()
plt.savefig(OUT_PATH + "charts/ml_forecast.png", dpi=150)
plt.show()

print("Models saved. Run notebook 06 for insight generation.")
