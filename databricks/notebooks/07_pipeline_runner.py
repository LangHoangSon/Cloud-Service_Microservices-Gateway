# Databricks notebook source
# MAGIC %md
# MAGIC # 07 — Pipeline Runner
# MAGIC Run all notebooks 01–06 in sequence.
# MAGIC Use this for scheduled runs or full reruns.

# COMMAND ----------
import time

NOTEBOOKS = [
    ("/FileStore/ecommerce/notebooks/01_data_loading",      "Data Loading"),
    ("/FileStore/ecommerce/notebooks/02_data_cleaning",     "Data Cleaning"),
    ("/FileStore/ecommerce/notebooks/03_feature_engineering","Feature Engineering"),
    ("/FileStore/ecommerce/notebooks/04_analytics",         "Analytics"),
    ("/FileStore/ecommerce/notebooks/05_ml_training",       "ML Training"),
    ("/FileStore/ecommerce/notebooks/06_insight_generation","Insight Generation"),
]

# COMMAND ----------
results = []
pipeline_start = time.time()

for path, name in NOTEBOOKS:
    print(f"▶  Running: {name}...")
    start = time.time()
    try:
        dbutils.notebook.run(path, timeout_seconds=3600)
        elapsed = time.time() - start
        results.append({"notebook": name, "status": "✅ OK", "time_s": round(elapsed, 1)})
        print(f"   ✅  {name} — {elapsed:.1f}s\n")
    except Exception as e:
        elapsed = time.time() - start
        results.append({"notebook": name, "status": f"❌ FAILED: {str(e)[:80]}", "time_s": round(elapsed, 1)})
        print(f"   ❌  {name} FAILED: {e}\n")
        break  # Stop pipeline on failure

# COMMAND ----------
total_time = time.time() - pipeline_start
print("=" * 55)
print("PIPELINE RUN SUMMARY")
print("=" * 55)
for r in results:
    print(f"  {r['status']}  {r['notebook']} ({r['time_s']}s)")
print("-" * 55)
print(f"  Total time: {total_time:.0f}s")

all_ok = all("OK" in r["status"] for r in results)
print(f"  Pipeline: {'✅ COMPLETE' if all_ok else '❌ INCOMPLETE'}")
print("=" * 55)
