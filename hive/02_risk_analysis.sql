-- ====================================================================
-- Script 02: Risk Assessment Engine (CTAS with ORC Storage)
-- Computes explainable risk scores and levels directly inside Apache Hive
-- ====================================================================

USE news_risk;

DROP TABLE IF EXISTS assessed_news;

CREATE TABLE assessed_news
STORED AS ORC
AS
SELECT
    article_id,
    title,
    content,
    source,
    published_at,
    url,
    category,
    sentiment_label,
    sentiment_compound,
    negative_intensity,
    severity_score,
    severity_keywords,
    ROUND(
        LEAST(
            100.0,
            GREATEST(0.0, (0.60 * negative_intensity) + (0.40 * severity_score))
        ),
        2
    ) AS risk_score,
    CASE
        WHEN ((0.60 * negative_intensity) + (0.40 * severity_score)) >= 75.0 THEN 'HIGH'
        WHEN ((0.60 * negative_intensity) + (0.40 * severity_score)) >= 40.0 THEN 'MEDIUM'
        ELSE 'LOW'
    END AS risk_level
FROM news_raw;
