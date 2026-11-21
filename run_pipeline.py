"""Main End-to-End Execution Pipeline for Big Data News Risk Assessment Platform.
Orchestrates preprocessing, text analytics, Docker Hive lifecycle, HiveQL queries, and exports.
"""

import sys
import os
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from utils.config import (
    RAW_DATA_PATH,
    PROCESSED_DATA_PATH,
    OUTPUTS_DIR,
    HIVE_DATABASE,
    HIVE_CONTAINER
)
from utils.logger import logger
from scripts.prepare_data import preprocess_news_dataset
from scripts.hive_runner import HiveRunner

def validate_exported_outputs() -> bool:
    """Validates that all required analytical CSV outputs were exported by Hive."""
    required_files = [
        "risk_summary.csv",
        "category_summary.csv",
        "source_summary.csv",
        "sentiment_summary.csv",
        "news_records.csv"
    ]
    missing = []
    for fname in required_files:
        fpath = OUTPUTS_DIR / fname
        if not fpath.exists() or fpath.stat().st_size == 0:
            missing.append(fname)

    if missing:
        logger.error(f"Validation failed: The following Hive output files are missing or empty: {', '.join(missing)}")
        return False

    logger.info("All required HiveQL output CSV files are verified and present in outputs/ directory.")
    return True

def run_pipeline() -> bool:
    """
    Executes the full 16-step automated pipeline:
    1. Verify Docker availability.
    2. Verify Hive container availability.
    3. Check HiveServer2 connectivity.
    4. Read CSV dataset.
    5. Validate and preprocess records.
    6. Perform sentiment analysis.
    7. Perform category classification.
    8. Perform severity detection.
    9. Generate enriched TSV file.
    10. Transfer file into Hive container.
    11. Execute Hive table creation and loading.
    12. Execute Hive risk assessment queries.
    13. Execute analytical HiveQL queries.
    14. Export Hive results to outputs directory.
    15. Validate exported results.
    16. Report execution status.
    """
    logger.info("======================================================================")
    logger.info(">>> BIG DATA RISK ASSESSMENT PIPELINE AUTOMATION STARTING <<<")
    logger.info("======================================================================")

    hive_runner = HiveRunner()

    # Step 1: Verify Docker availability
    logger.info("Step 1/16: Verifying Docker availability...")
    docker_ok, docker_msg = hive_runner.check_docker_available()
    if not docker_ok:
        logger.error(f"[FAILED] Docker is not available: {docker_msg}")
        logger.error("Please launch Docker Desktop and ensure the Docker daemon is running.")
        logger.error("Run: 'docker ps' in PowerShell to verify.")
        return False
    logger.info(f"[PASSED] {docker_msg}")

    # Step 2 & 3: Verify Hive container and HiveServer2
    logger.info("Step 2 & 3/16: Verifying Hive container and HiveServer2 readiness...")
    started, start_msg = hive_runner.ensure_container_started()
    if not started:
        logger.error(f"[FAILED] Hive container could not be started: {start_msg}")
        return False
    logger.info(f"[PASSED] {start_msg}")

    ready, ready_msg = hive_runner.check_hive_ready(retries=12, delay_sec=5)
    if not ready:
        logger.error(f"[FAILED] HiveServer2 connectivity check failed: {ready_msg}")
        logger.error("HiveServer2 inside the container is still initializing or port 10000 is blocked.")
        return False
    logger.info(f"[PASSED] {ready_msg}")

    # Steps 4, 5, 6, 7, 8, 9: Ingestion, Validation, NLP, Enriched TSV
    logger.info("Steps 4-9/16: Reading, preprocessing, and performing NLP text analysis...")
    try:
        enriched_df = preprocess_news_dataset(RAW_DATA_PATH, PROCESSED_DATA_PATH)
        logger.info(f"[PASSED] Preprocessing generated enriched TSV ({len(enriched_df)} articles).")
    except Exception as e:
        logger.error(f"[FAILED] Data preprocessing failed: {e}")
        return False

    # Step 10: Transfer TSV into Hive container
    logger.info("Step 10/16: Transferring enriched dataset to Hive container...")
    container_tsv = "/opt/hive/data/news_enriched.tsv"
    if not hive_runner.copy_file_to_container(PROCESSED_DATA_PATH, container_tsv):
        logger.error("[FAILED] Could not transfer TSV file into Docker container.")
        return False
    logger.info("[PASSED] TSV file transferred into container.")

    # Step 11: Execute Hive table creation & loading
    logger.info("Step 11/16: Executing Hive table creation (hive/01_create_tables.sql)...")
    ok1, out1 = hive_runner.execute_beeline_script(PROJECT_ROOT / "hive" / "01_create_tables.sql")
    if not ok1:
        logger.error(f"[FAILED] 01_create_tables.sql failed: {out1}")
        return False

    load_query = f"USE {HIVE_DATABASE}; LOAD DATA LOCAL INPATH '{container_tsv}' OVERWRITE INTO TABLE news_raw;"
    ok_load, out_load = hive_runner.execute_beeline_query(load_query)
    if not ok_load:
        logger.error(f"[FAILED] Loading data into news_raw failed: {out_load}")
        return False
    logger.info("[PASSED] 'news_raw' table created and loaded with records.")

    # Step 12: Execute Hive risk assessment CTAS
    logger.info("Step 12/16: Executing Hive risk assessment CTAS with ORC storage (hive/02_risk_analysis.sql)...")
    ok2, out2 = hive_runner.execute_beeline_script(PROJECT_ROOT / "hive" / "02_risk_analysis.sql")
    if not ok2:
        logger.error(f"[FAILED] 02_risk_analysis.sql failed: {out2}")
        return False
    logger.info("[PASSED] 'assessed_news' ORC table successfully built by HiveQL.")

    # Steps 13 & 14: Execute analytical HiveQL queries and export to CSV
    logger.info("Steps 13-14/16: Executing analytical HiveQL queries and exporting outputs...")
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    export_queries = {
        "risk_summary.csv": f"""
            USE {HIVE_DATABASE};
            SELECT risk_level, COUNT(*) AS article_count,
                   ROUND(AVG(risk_score), 2) AS avg_risk_score,
                   ROUND(AVG(negative_intensity), 2) AS avg_negative_intensity,
                   ROUND(AVG(severity_score), 2) AS avg_severity_score
            FROM assessed_news
            GROUP BY risk_level
            ORDER BY avg_risk_score DESC;
        """,
        "category_summary.csv": f"""
            USE {HIVE_DATABASE};
            SELECT category, COUNT(*) AS total_articles,
                   ROUND(AVG(risk_score), 2) AS avg_risk_score,
                   ROUND(AVG(severity_score), 2) AS avg_severity_score,
                   SUM(CASE WHEN risk_level = 'HIGH' THEN 1 ELSE 0 END) AS high_risk_count,
                   SUM(CASE WHEN risk_level = 'MEDIUM' THEN 1 ELSE 0 END) AS medium_risk_count,
                   SUM(CASE WHEN risk_level = 'LOW' THEN 1 ELSE 0 END) AS low_risk_count
            FROM assessed_news
            GROUP BY category
            ORDER BY avg_risk_score DESC;
        """,
        "source_summary.csv": f"""
            USE {HIVE_DATABASE};
            SELECT source, COUNT(*) AS total_articles,
                   ROUND(AVG(risk_score), 2) AS avg_risk_score,
                   SUM(CASE WHEN risk_level = 'HIGH' THEN 1 ELSE 0 END) AS high_risk_count,
                   ROUND(AVG(sentiment_compound), 4) AS avg_sentiment_compound
            FROM assessed_news
            GROUP BY source
            ORDER BY total_articles DESC, avg_risk_score DESC;
        """,
        "sentiment_summary.csv": f"""
            USE {HIVE_DATABASE};
            SELECT sentiment_label, COUNT(*) AS article_count,
                   ROUND(AVG(sentiment_compound), 4) AS avg_compound,
                   ROUND(AVG(risk_score), 2) AS avg_risk_score
            FROM assessed_news
            GROUP BY sentiment_label
            ORDER BY article_count DESC;
        """,
        "trend_summary.csv": f"""
            USE {HIVE_DATABASE};
            SELECT SUBSTR(published_at, 1, 10) AS publication_date,
                   COUNT(*) AS article_count,
                   ROUND(AVG(risk_score), 2) AS avg_risk_score,
                   SUM(CASE WHEN risk_level = 'HIGH' THEN 1 ELSE 0 END) AS high_risk_count
            FROM assessed_news
            GROUP BY SUBSTR(published_at, 1, 10)
            ORDER BY publication_date ASC;
        """,
        "news_records.csv": f"""
            USE {HIVE_DATABASE};
            SELECT article_id, title, content, source, published_at, url,
                   category, sentiment_label, sentiment_compound,
                   negative_intensity, severity_score, severity_keywords,
                   risk_score, risk_level
            FROM assessed_news
            ORDER BY risk_score DESC;
        """
    }

    for fname, qry in export_queries.items():
        out_path = OUTPUTS_DIR / fname
        ok_exp, out_exp = hive_runner.execute_beeline_query(qry, output_csv=out_path)
        if not ok_exp:
            logger.error(f"[FAILED] Exporting {fname} failed: {out_exp}")
            return False

    # Step 15: Validate exported results
    logger.info("Step 15/16: Validating exported analytical CSV files...")
    if not validate_exported_outputs():
        return False

    # Step 16: Report success
    logger.info("======================================================================")
    logger.info("Step 16/16: PIPELINE EXECUTION COMPLETED SUCCESSFULLY!")
    logger.info(f"Apache Hive 4.0.0 finished computing risk scores and analytics.")
    logger.info(f"Analytical exports are ready in: {OUTPUTS_DIR}")
    logger.info("======================================================================")
    return True

if __name__ == "__main__":
    success = run_pipeline()
    sys.exit(0 if success else 1)
