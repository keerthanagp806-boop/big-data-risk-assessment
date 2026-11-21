"""Severity detection module using configurable keyword rules."""

import sys
from pathlib import Path
import re
from typing import Dict, Tuple, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from utils.config import SEVERITY_KEYWORDS
from utils.logger import logger

class NewsSeverityDetector:
    """Detects emergency and severity-related terms and calculates a 0-100 severity score."""

    def __init__(self, keywords_dict: Dict[str, int] | None = None):
        self.keywords = keywords_dict or SEVERITY_KEYWORDS
        self._compiled_patterns = {}
        for kw, weight in self.keywords.items():
            escaped = re.escape(kw.lower())
            p = r"\b" + escaped + r"\b" if re.match(r"^\w", kw) else escaped
            self._compiled_patterns[kw] = (re.compile(p, re.IGNORECASE), weight)

    def detect(self, title: str, content: str) -> Tuple[float, str]:
        """
        Detects severity keywords and computes a severity score between 0 and 100.
        Returns (severity_score, matched_keywords_str).
        """
        combined = f"{str(title or '')} {str(content or '')}".lower()
        matched: List[str] = []
        raw_score = 0.0

        for kw, (pattern, weight) in self._compiled_patterns.items():
            matches = len(pattern.findall(combined))
            if matches > 0:
                matched.append(kw)
                # Cap contribution of repeated occurrences of same keyword
                capped_count = min(matches, 3)
                raw_score += (weight * capped_count * 5.0)

        # Scale to 0-100
        severity_score = min(100.0, max(0.0, round(raw_score, 2)))
        matched_str = "; ".join(matched) if matched else "None"
        return severity_score, matched_str

def apply_severity_detection(df: pd.DataFrame) -> pd.DataFrame:
    """Applies severity detection across all records in the DataFrame."""
    detector = NewsSeverityDetector()
    enriched = df.copy()

    scores = []
    matched_list = []

    for _, row in enriched.iterrows():
        score, matched = detector.detect(row.get("title", ""), row.get("content", ""))
        scores.append(score)
        matched_list.append(matched)

    enriched["severity_score"] = scores
    enriched["severity_keywords"] = matched_list
    logger.info(f"Severity detection completed. Average severity score: {round(enriched['severity_score'].mean(), 2)}")
    return enriched
