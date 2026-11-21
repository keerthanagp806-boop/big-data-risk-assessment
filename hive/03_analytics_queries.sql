-- ====================================================================
-- Script 03: HiveQL Analytical Queries
-- Executes aggregations, source comparisons, and risk distributions
-- ====================================================================

USE news_risk;

-- 1. Overall Risk Level Summary
SELECT 
    risk_level,
    COUNT(*) AS article_count,
    ROUND(AVG(risk_score), 2) AS avg_risk_score,
    ROUND(AVG(negative_intensity), 2) AS avg_negative_intensity,
    ROUND(AVG(severity_score), 2) AS avg_severity_score
FROM assessed_news
GROUP BY risk_level
ORDER BY avg_risk_score DESC;

-- 2. Category Summary & Cross Analysis
SELECT 
    category,
    COUNT(*) AS total_articles,
    ROUND(AVG(risk_score), 2) AS avg_risk_score,
    ROUND(AVG(severity_score), 2) AS avg_severity_score,
    SUM(CASE WHEN risk_level = 'HIGH' THEN 1 ELSE 0 END) AS high_risk_count,
    SUM(CASE WHEN risk_level = 'MEDIUM' THEN 1 ELSE 0 END) AS medium_risk_count,
    SUM(CASE WHEN risk_level = 'LOW' THEN 1 ELSE 0 END) AS low_risk_count
FROM assessed_news
GROUP BY category
ORDER BY avg_risk_score DESC;

-- 3. Source Summary
SELECT 
    source,
    COUNT(*) AS total_articles,
    ROUND(AVG(risk_score), 2) AS avg_risk_score,
    SUM(CASE WHEN risk_level = 'HIGH' THEN 1 ELSE 0 END) AS high_risk_count,
    ROUND(AVG(sentiment_compound), 4) AS avg_sentiment_compound
FROM assessed_news
GROUP BY source
ORDER BY total_articles DESC, avg_risk_score DESC;

-- 4. Sentiment Summary
SELECT 
    sentiment_label,
    COUNT(*) AS article_count,
    ROUND(AVG(sentiment_compound), 4) AS avg_compound,
    ROUND(AVG(risk_score), 2) AS avg_risk_score
FROM assessed_news
GROUP BY sentiment_label
ORDER BY article_count DESC;

-- 5. Daily Publication & Risk Trend
SELECT 
    SUBSTR(published_at, 1, 10) AS publication_date,
    COUNT(*) AS article_count,
    ROUND(AVG(risk_score), 2) AS avg_risk_score,
    SUM(CASE WHEN risk_level = 'HIGH' THEN 1 ELSE 0 END) AS high_risk_count
FROM assessed_news
GROUP BY SUBSTR(published_at, 1, 10)
ORDER BY publication_date ASC;

-- 6. Full Assessed News Records Export
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
    risk_score,
    risk_level
FROM assessed_news
ORDER BY risk_score DESC;
