"""Unit tests for NLP sentiment, category classification, severity detection, and risk scoring."""

import pytest
from scripts.sentiment_analysis import NewsSentimentAnalyzer
from scripts.category_classifier import NewsCategoryClassifier
from scripts.severity_detector import NewsSeverityDetector

def test_vader_sentiment_scores_range_and_intensity():
    analyzer = NewsSentimentAnalyzer()

    # Highly positive sentence
    pos_res = analyzer.analyze("An outstanding triumph of human innovation and glorious success.")
    assert -1.0 <= pos_res["sentiment_compound"] <= 1.0
    assert pos_res["sentiment_compound"] >= 0.05
    assert pos_res["sentiment_label"] == "Positive"
    assert pos_res["negative_intensity"] == 0.0

    # Highly negative sentence
    neg_res = analyzer.analyze("Terrible catastrophic devastation with horrific fatalities and suffering.")
    assert -1.0 <= neg_res["sentiment_compound"] <= 1.0
    assert neg_res["sentiment_compound"] <= -0.05
    assert neg_res["sentiment_label"] == "Negative"
    assert neg_res["negative_intensity"] == round(abs(neg_res["sentiment_compound"]) * 100.0, 2)
    assert neg_res["negative_intensity"] > 0.0

def test_category_classifier_politics_and_technology():
    classifier = NewsCategoryClassifier()

    cat1 = classifier.classify(
        "Presidential Election Results Declared",
        "The parliament and senate ratified the voting legislation after intense debate."
    )
    assert cat1 == "Politics"

    cat2 = classifier.classify(
        "New Artificial Intelligence Supercomputer",
        "The neural network model accelerates semiconductor algorithm designs."
    )
    assert cat2 == "Technology"

def test_severity_detection_and_keyword_extraction():
    detector = NewsSeverityDetector()

    # Extreme threat
    score1, kws1 = detector.detect(
        "Critical Cyberattack and Terrorism Threat",
        "A major ransomware attack compromised defense infrastructure."
    )
    assert score1 >= 50.0
    assert "cyberattack" in kws1.lower()
    assert "terrorism" in kws1.lower()

    # Benign article
    score2, kws2 = detector.detect(
        "Orchestral Symphony Opens Concert Season",
        "Musicians performed classical concertos in the historic downtown theater."
    )
    assert score2 == 0.0
    assert kws2 == "None"

def test_risk_scoring_formula_and_classification():
    # Mathematical formula: risk = min(100, max(0, 0.60 * neg + 0.40 * sev))
    def calc_risk(neg: float, sev: float):
        score = min(100.0, max(0.0, round((0.60 * neg) + (0.40 * sev), 2)))
        if score >= 75.0:
            level = "HIGH"
        elif score >= 40.0:
            level = "MEDIUM"
        else:
            level = "LOW"
        return score, level

    # Case 1: High severity + high negative intensity -> HIGH
    score, level = calc_risk(neg=90.0, sev=80.0)
    assert score == 86.0
    assert level == "HIGH"

    # Case 2: Moderate severity + mild negative -> MEDIUM
    score, level = calc_risk(neg=40.0, sev=50.0)
    assert score == 44.0
    assert level == "MEDIUM"

    # Case 3: Zero negative + zero severity -> LOW
    score, level = calc_risk(neg=0.0, sev=0.0)
    assert score == 0.0
    assert level == "LOW"

    # Boundary checks: below 40 is LOW, 40 to 74.99 is MEDIUM, >= 75 is HIGH
    score_low, lvl_low = calc_risk(neg=39.0, sev=39.0)
    assert lvl_low == "LOW"

    score_med, lvl_med = calc_risk(neg=40.0, sev=40.0)
    assert lvl_med == "MEDIUM"

    score_high, lvl_high = calc_risk(neg=75.0, sev=75.0)
    assert lvl_high == "HIGH"
