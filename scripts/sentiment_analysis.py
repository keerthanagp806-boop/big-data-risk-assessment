"""Sentiment analysis module using NLTK VADER."""

import sys
from pathlib import Path
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from utils.logger import logger

# Add local venv nltk_data path
local_nltk_dir = PROJECT_ROOT / ".venv" / "nltk_data"
if local_nltk_dir.exists() and str(local_nltk_dir) not in nltk.data.path:
    nltk.data.path.insert(0, str(local_nltk_dir))

# Ensure VADER lexicon is downloaded
try:
    nltk.data.find("sentiment/vader_lexicon.zip")
except (LookupError, OSError):
    try:
        nltk.download("vader_lexicon", quiet=True)
    except Exception as e:
        logger.warning(f"Failed to auto-download vader_lexicon: {e}")

class NewsSentimentAnalyzer:
    """Wrapper for VADER Sentiment Analysis tailored for news articles."""

    def __init__(self):
        try:
            self.sia = SentimentIntensityAnalyzer()
        except Exception:
            nltk.download("vader_lexicon", quiet=True)
            self.sia = SentimentIntensityAnalyzer()

    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyzes the text and returns compound score, classification label,
        and negative intensity (0 to 100).
        """
        if not text or not isinstance(text, str) or not text.strip():
            return {
                "sentiment_compound": 0.0,
                "sentiment_label": "Neutral",
                "negative_intensity": 0.0
            }

        scores = self.sia.polarity_scores(text)
        compound = round(float(scores["compound"]), 4)

        if compound >= 0.05:
            label = "Positive"
            neg_intensity = 0.0
        elif compound <= -0.05:
            label = "Negative"
            neg_intensity = round(abs(compound) * 100.0, 2)
        else:
            label = "Neutral"
            neg_intensity = 0.0

        return {
            "sentiment_compound": compound,
            "sentiment_label": label,
            "negative_intensity": neg_intensity
        }

def apply_sentiment_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies sentiment analysis to DataFrame combining title and content.
    Adds sentiment_label, sentiment_compound, and negative_intensity columns.
    """
    analyzer = NewsSentimentAnalyzer()
    enriched = df.copy()

    compounds = []
    labels = []
    intensities = []

    for _, row in enriched.iterrows():
        # Title usually carries strong emotional focus; combine title + content
        text = f"{str(row.get('title', ''))}. {str(row.get('content', ''))}"
        result = analyzer.analyze(text)
        compounds.append(result["sentiment_compound"])
        labels.append(result["sentiment_label"])
        intensities.append(result["negative_intensity"])

    enriched["sentiment_compound"] = compounds
    enriched["sentiment_label"] = labels
    enriched["negative_intensity"] = intensities
    
    logger.info(f"Sentiment analysis completed for {len(enriched)} articles.")
    return enriched
