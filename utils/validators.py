"""Data validation utilities for news ingestion."""

from typing import Tuple, List
import pandas as pd
from utils.logger import logger

REQUIRED_COLUMNS = [
    "article_id",
    "title",
    "content",
    "source",
    "published_at",
    "url"
]

def validate_dataset_schema(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Validates whether the incoming DataFrame satisfies the required schema.
    Returns (is_valid, list_of_errors).
    """
    errors: List[str] = []

    if df is None or df.empty:
        errors.append("Dataset is empty or None.")
        return False, errors

    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        errors.append(f"Missing required columns: {', '.join(missing_cols)}")

    return len(errors) == 0, errors

def clean_and_validate_records(df: pd.DataFrame) -> Tuple[pd.DataFrame, dict]:
    """
    Validates and performs basic hygiene checks on news records:
    - Checks required columns
    - Drops duplicates by article_id and title
    - Standardizes published_at
    - Filters out rows with empty title or content
    """
    stats = {
        "initial_count": len(df),
        "missing_dropped": 0,
        "duplicates_dropped": 0,
        "invalid_dates": 0,
        "final_count": 0
    }

    is_valid, errors = validate_dataset_schema(df)
    if not is_valid:
        raise ValueError(f"Schema validation failed: {'; '.join(errors)}")

    # Work on a copy
    cleaned = df.copy()

    # Drop null title or content
    before_null = len(cleaned)
    cleaned = cleaned.dropna(subset=["title", "content"])
    cleaned = cleaned[cleaned["title"].str.strip() != ""]
    cleaned = cleaned[cleaned["content"].str.strip() != ""]
    stats["missing_dropped"] = before_null - len(cleaned)

    # Deduplicate by article_id or title
    before_dup = len(cleaned)
    cleaned = cleaned.drop_duplicates(subset=["article_id"])
    cleaned = cleaned.drop_duplicates(subset=["title"])
    stats["duplicates_dropped"] = before_dup - len(cleaned)

    # Standardize dates
    cleaned["published_at"] = pd.to_datetime(cleaned["published_at"], errors="coerce")
    invalid_dates = cleaned["published_at"].isna().sum()
    stats["invalid_dates"] = int(invalid_dates)
    
    # Fill invalid dates with current timestamp to avoid losing records
    now_ts = pd.Timestamp.now().normalize()
    cleaned["published_at"] = cleaned["published_at"].fillna(now_ts)
    cleaned["published_at"] = cleaned["published_at"].dt.strftime("%Y-%m-%d %H:%M:%S")

    stats["final_count"] = len(cleaned)
    logger.info(f"Dataset validation completed: {stats}")
    return cleaned, stats
