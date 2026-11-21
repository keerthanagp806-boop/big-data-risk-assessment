-- ====================================================================
-- Script 01: Create Database and Ingestion Tables
-- Engine: Apache Hive 4.0.0
-- ====================================================================

CREATE DATABASE IF NOT EXISTS news_risk;
USE news_risk;

DROP TABLE IF EXISTS news_raw;

CREATE TABLE news_raw (
    article_id STRING,
    title STRING,
    content STRING,
    source STRING,
    published_at STRING,
    url STRING,
    category STRING,
    sentiment_label STRING,
    sentiment_compound DOUBLE,
    negative_intensity DOUBLE,
    severity_score DOUBLE,
    severity_keywords STRING
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY '\t'
LINES TERMINATED BY '\n'
STORED AS TEXTFILE;
