"""Category classification module using configurable keyword rules."""

import sys
from pathlib import Path
import re
from typing import Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from utils.config import CATEGORY_KEYWORDS
from utils.logger import logger

class NewsCategoryClassifier:
    """Classifies news articles into predefined categories based on keyword occurrences."""

    def __init__(self, keywords_dict: Dict[str, List[str]] | None = None):
        self.keywords = keywords_dict or CATEGORY_KEYWORDS
        # Compile word-boundary regex patterns for accurate matching
        self._compiled_patterns = {}
        for cat, kws in self.keywords.items():
            patterns = []
            for kw in kws:
                escaped = re.escape(kw.lower())
                # Use word boundary if keyword starts/ends with alphanumeric
                p = r"\b" + escaped + r"\b" if re.match(r"^\w", kw) else escaped
                patterns.append(re.compile(p, re.IGNORECASE))
            self._compiled_patterns[cat] = patterns

    def classify(self, title: str, content: str) -> str:
        """
        Classifies article text into one of the categories.
        Titles are given higher weighting (2x).
        """
        title_str = str(title or "").lower()
        content_str = str(content or "").lower()

        scores: Dict[str, int] = {cat: 0 for cat in self.keywords}

        for cat, patterns in self._compiled_patterns.items():
            for pat in patterns:
                # 2 points per match in title, 1 point per match in content
                t_matches = len(pat.findall(title_str))
                c_matches = len(pat.findall(content_str))
                scores[cat] += (t_matches * 2) + c_matches

        # Find category with max score
        best_cat = "Other"
        max_score = 0
        for cat, score in scores.items():
            if score > max_score:
                max_score = score
                best_cat = cat

        return best_cat

def apply_category_classification(df: pd.DataFrame) -> pd.DataFrame:
    """Applies category classification across all articles in the DataFrame."""
    classifier = NewsCategoryClassifier()
    enriched = df.copy()

    categories = [
        classifier.classify(row.get("title", ""), row.get("content", ""))
        for _, row in enriched.iterrows()
    ]
    enriched["category"] = categories
    logger.info(f"Category classification completed. Distribution: {enriched['category'].value_counts().to_dict()}")
    return enriched
