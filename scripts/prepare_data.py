"""Data preparation and preprocessing pipeline."""

import sys
import re
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from utils.config import RAW_DATA_PATH, PROCESSED_DATA_PATH, PROCESSED_DATA_DIR
from utils.logger import logger
from utils.validators import clean_and_validate_records
from scripts.sentiment_analysis import apply_sentiment_analysis
from scripts.category_classifier import apply_category_classification
from scripts.severity_detector import apply_severity_detection

def clean_text(text: str) -> str:
    """
    Normalizes text by removing line breaks, tabs, and excess whitespace
    to ensure tab-separated file integrity for Apache Hive.
    """
    if not isinstance(text, str):
        return ""
    # Replace tabs and newlines with a single space
    cleaned = re.sub(r"[\r\n\t]+", " ", text)
    # Collapse multiple spaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned

def preprocess_news_dataset(
    input_path: Path = RAW_DATA_PATH,
    output_path: Path = PROCESSED_DATA_PATH
) -> pd.DataFrame:
    """
    Loads raw CSV dataset, cleans, validates, performs text analysis
    (sentiment, category, severity), and exports an enriched TSV file.
    """
    logger.info(f"Starting data preprocessing from: {input_path}")
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found at: {input_path}")

    # Read raw dataset
    df = pd.read_csv(input_path, encoding="utf-8")
    logger.info(f"Loaded {len(df)} raw records.")

    # Validation and cleaning
    df, stats = clean_and_validate_records(df)

    # Normalize text fields for title, content, source
    df["title"] = df["title"].apply(clean_text)
    df["content"] = df["content"].apply(clean_text)
    df["source"] = df["source"].apply(clean_text)
    df["url"] = df["url"].apply(clean_text)

    # Apply Text Analytics
    logger.info("Applying NLP category classification...")
    df = apply_category_classification(df)

    logger.info("Applying VADER sentiment analysis...")
    df = apply_sentiment_analysis(df)

    logger.info("Applying rule-based severity detection...")
    df = apply_severity_detection(df)

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Required column order matching Hive schema
    hive_columns = [
        "article_id",
        "title",
        "content",
        "source",
        "published_at",
        "url",
        "category",
        "sentiment_label",
        "sentiment_compound",
        "negative_intensity",
        "severity_score",
        "severity_keywords"
    ]

    export_df = df[hive_columns]

    # Save to TSV without index, tab-separated, no header for Hive loading convenience
    export_df.to_csv(output_path, sep="\t", index=False, header=False, encoding="utf-8")
    logger.info(f"Successfully generated enriched TSV at {output_path} ({len(export_df)} records).")

    return df

if __name__ == "__main__":
    preprocess_news_dataset()
