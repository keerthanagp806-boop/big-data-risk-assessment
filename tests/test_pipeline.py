"""Integration tests for pipeline automation, Docker/Hive readiness, and outputs verification."""

import pytest
from pathlib import Path
import pandas as pd
from utils.config import RAW_DATA_PATH, PROCESSED_DATA_PATH, OUTPUTS_DIR
from scripts.prepare_data import preprocess_news_dataset
from scripts.hive_runner import HiveRunner
from run_pipeline import validate_exported_outputs

def test_preprocessing_pipeline_generates_valid_tsv():
    """Verifies that the Python preprocessing pipeline creates the enriched TSV with all required columns."""
    assert RAW_DATA_PATH.exists(), f"Sample raw dataset missing at: {RAW_DATA_PATH}"
    df = preprocess_news_dataset(RAW_DATA_PATH, PROCESSED_DATA_PATH)
    assert PROCESSED_DATA_PATH.exists()
    assert len(df) >= 30, "Dataset must have at least 30 articles as per PRD requirements."
    
    # Check that required columns exist in output
    required_cols = [
        "article_id", "title", "content", "source", "published_at",
        "url", "category", "sentiment_label", "sentiment_compound",
        "negative_intensity", "severity_score", "severity_keywords"
    ]
    for col in required_cols:
        assert col in df.columns

def test_docker_and_hive_diagnostics():
    """
    Checks Docker and Hive diagnostics.
    If Docker is not running, asserts that the runner correctly reports failure
    and does NOT claim success falsely.
    """
    runner = HiveRunner()
    docker_ok, docker_msg = runner.check_docker_available()
    assert isinstance(docker_ok, bool)
    assert isinstance(docker_msg, str)
    assert len(docker_msg) > 0

    if not docker_ok:
        pytest.skip(f"Docker is not running ({docker_msg}). Skipping live HiveServer2 container test.")

    # If Docker is available, verify container check
    container_ok, container_msg = runner.check_container_status()
    assert isinstance(container_ok, bool)

def test_outputs_structure_when_available():
    """If analytical outputs exist, validates their schema and data types."""
    if not (OUTPUTS_DIR / "risk_summary.csv").exists():
        pytest.skip("Hive outputs have not been generated yet. Skipping export schema check.")

    assert validate_exported_outputs() is True

    # Validate news_records.csv contains risk_score and risk_level
    records_df = pd.read_csv(OUTPUTS_DIR / "news_records.csv")
    assert "risk_score" in records_df.columns
    assert "risk_level" in records_df.columns
    assert records_df["risk_score"].min() >= 0.0
    assert records_df["risk_score"].max() <= 100.0
    assert set(records_df["risk_level"].unique()).issubset({"LOW", "MEDIUM", "HIGH"})
