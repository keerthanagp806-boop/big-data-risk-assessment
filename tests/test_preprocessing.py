"""Unit tests for news data ingestion, validation, and preprocessing."""

import pytest
import pandas as pd
from pathlib import Path
from utils.validators import validate_dataset_schema, clean_and_validate_records
from scripts.prepare_data import clean_text

def test_clean_text_removes_tabs_and_newlines():
    raw = "Breaking News:\tMassive event\r\noccurred today.\t Details follow.  "
    cleaned = clean_text(raw)
    assert "\t" not in cleaned
    assert "\n" not in cleaned
    assert "\r" not in cleaned
    assert "  " not in cleaned
    assert cleaned == "Breaking News: Massive event occurred today. Details follow."

def test_validate_dataset_schema_success():
    df = pd.DataFrame({
        "article_id": ["A1"],
        "title": ["Test Title"],
        "content": ["Test Content"],
        "source": ["Test Source"],
        "published_at": ["2026-03-01 10:00:00"],
        "url": ["https://example.com/1"]
    })
    is_valid, errors = validate_dataset_schema(df)
    assert is_valid is True
    assert len(errors) == 0

def test_validate_dataset_schema_missing_columns():
    df = pd.DataFrame({
        "article_id": ["A1"],
        "title": ["Test Title"]
    })
    is_valid, errors = validate_dataset_schema(df)
    assert is_valid is False
    assert any("Missing required columns" in e for e in errors)

def test_clean_and_validate_records_deduplication():
    df = pd.DataFrame({
        "article_id": ["A1", "A2", "A3"],
        "title": ["Duplicate Title", "Duplicate Title", "Unique Title"],
        "content": ["Content 1", "Content 2", "Content 3"],
        "source": ["Source A", "Source B", "Source C"],
        "published_at": ["2026-03-01", "2026-03-02", "2026-03-03"],
        "url": ["http://a", "http://b", "http://c"]
    })
    cleaned, stats = clean_and_validate_records(df)
    assert stats["duplicates_dropped"] == 1
    assert len(cleaned) == 2

def test_clean_and_validate_records_empty_rows_dropped():
    df = pd.DataFrame({
        "article_id": ["A1", "A2"],
        "title": ["Valid Title", ""],
        "content": ["", "Valid Content"],
        "source": ["Source A", "Source B"],
        "published_at": ["2026-03-01", "2026-03-02"],
        "url": ["http://a", "http://b"]
    })
    cleaned, stats = clean_and_validate_records(df)
    assert len(cleaned) == 0
    assert stats["missing_dropped"] == 2
