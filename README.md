# Big Data Risk Assessment for News Media Using Apache Hadoop & Apache Hive

An end-to-end Big Data Analytics platform that ingests, cleans, analyzes, and evaluates potentially high-risk news content using **Apache Hive 4.0.0**, **Hadoop ecosystem**, **VADER Sentiment Analysis**, **Rule-Based Severity Detection**, and an interactive **Streamlit** dashboard with **Plotly** visualizations.

---

## 1. Architecture Overview

```
                      NEWS DATA INPUT
                      (data/raw/news.csv)
                              │
                              ▼
                      DATA INGESTION
                      (Python + Pandas)
                              │
                              ▼
                      DATA PREPROCESSING
             (Cleaning + Validation + Deduplication)
                              │
                              ▼
                        TEXT ANALYSIS
          ┌───────────────────┴───────────────────┐
          ▼                                       ▼
  VADER Sentiment Analysis                NLP Keyword Classifier &
  (Compound score: -1 to +1)              Rule-Based Severity Detector
          └───────────────────┬───────────────────┘
                              │
                              ▼
                      PROCESSED NEWS DATA
                (data/processed/news_enriched.tsv)
                              │
                              ▼
                    APACHE HIVE 4.0.0 (DOCKER)
        ┌──────────────────────────────────────────────┐
        │ Database: news_risk                          │
        │ Table 1: news_raw (Delimited TextFile)       │
        │ Table 2: assessed_news (ORC Format via CTAS) │
        └──────────────────────────────────────────────┘
                              │
                              ▼
                       HIVEQL ANALYTICS
           (Risk Calculation: 60% Negative + 40% Severity
            Category, Source, Trend, & Cross Aggregations)
                              │
                              ▼
                     QUERY RESULT EXPORT
                 (outputs/*.csv output files)
                              │
                              ▼
                    STREAMLIT DASHBOARD
             (6 Interactive Analytical Pages + Plotly)
```

---

## 2. Risk Assessment Methodology

All final risk calculations are computed directly inside **Apache Hive** using HiveQL:

### Signal 1: Negative Intensity (Weight: 60%)
- For negative sentiment ($Compound \le -0.05$):
  $$\text{negative\_intensity} = |\text{sentiment\_compound}| \times 100$$
- For positive / neutral sentiment:
  $$\text{negative\_intensity} = 0$$

### Signal 2: Severity Score (Weight: 40%)
- Keyword-based severity detection identifying emergency, conflict, violence, terrorism, disaster, cyberattack, and financial collapse terms (scaled from 0 to 100).

### Final Explainable Risk Score:
$$\text{risk\_score} = \min\left(100, \max\left(0, (0.60 \times \text{negative\_intensity}) + (0.40 \times \text{severity\_score})\right)\right)$$

### Risk Classification:
- **LOW RISK**: $\text{risk\_score} < 40$
- **MEDIUM RISK**: $40 \le \text{risk\_score} < 75$
- **HIGH RISK**: $\text{risk\_score} \ge 75$

> **Academic Disclaimer:** This is an academic analytical prototype for risk assessment demonstration. It is not an automated fact-checking authority. High risk does not imply misinformation, and negative sentiment alone does not indicate danger or false reporting.

---

## 3. Project Directory Structure

```
Big Data Risk Assessment/
├── data/
│   ├── raw/
│   │   └── news.csv               # Bundled sample dataset with 35 realistic DEMO articles
│   └── processed/
│       └── news_enriched.tsv      # Preprocessed, tab-separated file for Hive ingestion
├── scripts/
│   ├── prepare_data.py            # Cleans, deduplicates, and applies NLP analytics
│   ├── sentiment_analysis.py      # VADER sentiment intensity analyzer
│   ├── category_classifier.py     # Multi-category keyword classifier
│   ├── severity_detector.py       # Rule-based severity scoring and keyword detection
│   └── hive_runner.py             # Docker container lifecycle and Beeline execution
├── hive/
│   ├── 01_create_tables.sql       # Creates news_risk database and news_raw table
│   ├── 02_risk_analysis.sql       # Executes Hive CTAS for assessed_news (ORC)
│   └── 03_analytics_queries.sql   # Executes analytical aggregations and risk summaries
├── outputs/
│   ├── risk_summary.csv           # HiveQL risk level distribution
│   ├── category_summary.csv       # HiveQL category risk analysis
│   ├── source_summary.csv         # HiveQL source comparisons
│   ├── sentiment_summary.csv      # HiveQL sentiment breakdown
│   ├── trend_summary.csv          # HiveQL publication & risk timeline
│   └── news_records.csv           # HiveQL complete assessed news records
├── utils/
│   ├── config.py                  # Central configuration and keyword dictionaries
│   ├── validators.py              # Schema and record validation routines
│   └── logger.py                  # Structured logging configuration
├── tests/
│   ├── test_preprocessing.py      # Tests for text cleaning and validation
│   ├── test_risk_scoring.py       # Tests for VADER, categories, severity, and risk math
│   └── test_pipeline.py           # Integration and Hive readiness tests
├── dashboard.py                   # 6-page interactive Streamlit dashboard
├── run_pipeline.py                # 16-step automated end-to-end execution pipeline
├── requirements.txt               # Python package dependencies
├── .env.example                   # Environment configuration template
├── .gitignore                     # Git ignore rules
└── README.md                      # Documentation and operational guide
```

---

## 4. Prerequisites

1. **Python**: Python 3.10, 3.11, or 3.12 (Python 3.12 verified in this workspace).
2. **Docker Desktop**: With WSL 2 backend enabled on Windows.
3. **PowerShell**: Windows PowerShell or PowerShell 7.

---

## 5. Setup & Execution Guide (Windows PowerShell)

### Step 1: Clone or Navigate to Project Folder
```powershell
cd "c:\Users\Keerthana\OneDrive\Desktop\Big Data Risk Assessment"
```

### Step 2: Create and Activate Python Virtual Environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Setup and Start Apache Hive 4.0.0 via Docker
Ensure Docker Desktop is open and running, then execute:

```powershell
# 1. Pull the official Apache Hive 4.0.0 Docker image
docker pull apache/hive:4.0.0

# 2. Create a persistent volume for the Hive warehouse
docker volume create hive_warehouse

# 3. Launch the HiveServer2 container
docker run -d --name hive4 -p 10000:10000 -p 10002:10002 -v hive_warehouse:/opt/hive/data/warehouse --env SERVICE_NAME=hiveserver2 apache/hive:4.0.0

# 4. Verify that the container is running
docker ps
```

*Note: HiveServer2 typically takes 20-30 seconds to initialize Derby metastore and open port 10000.*

### Step 4: Run the Automated Big Data Pipeline
Execute the 16-step end-to-end Python-to-Hive orchestration script:

```powershell
python run_pipeline.py
```

The script will automatically:
1. Verify Docker daemon availability.
2. Confirm Hive container status and wait for HiveServer2 readiness.
3. Validate raw CSV records and perform data hygiene.
4. Execute NLP category classification and VADER sentiment analysis.
5. Compute severity scores and generate `data/processed/news_enriched.tsv`.
6. Transfer the TSV dataset into the Hive container via `docker cp`.
7. Execute `hive/01_create_tables.sql` via Beeline CLI.
8. Load data into `news_risk.news_raw`.
9. Execute `hive/02_risk_analysis.sql` to compute risk scores in Hive and build `news_risk.assessed_news` (ORC format).
10. Execute analytical HiveQL queries and export clean CSVs into `outputs/`.
11. Validate exported files and report pipeline execution status.

### Step 5: Launch the Interactive Streamlit Dashboard
```powershell
streamlit run dashboard.py
```
Open your browser to: **http://localhost:8501**

---

## 6. Dashboard Features (6 Interactive Pages)

1. **Overview Dashboard**:
   - High-level KPIs: Total Articles, High-Risk Count, Medium-Risk Count, Low-Risk Count, Average Risk Score, Active Sources, Categories.
   - Interactive Plotly Charts: Risk Donut Chart, Category Volume, Average Risk by Category, Daily Volume Trends, Sentiment Distribution, Top Sources.
   - Live analytical summary synthesized from Hive results.

2. **News Explorer**:
   - Filterable data table by Category, Risk Level, Sentiment Polarity, and News Source.
   - Keyword text search across titles and article bodies.
   - Article inspection card showing full content, source link, and detailed signal breakdown (VADER compound, negative intensity, severity score, detected keywords, and final risk formula).

3. **Risk Analytics**:
   - Top 10 High-Risk Articles horizontal ranking.
   - Category vs. Risk Level Heatmap.
   - Source-wise average risk comparison with high-risk article counts.
   - Time-series dual-axis chart tracking daily average risk vs high-risk publication spikes.

4. **Sentiment Analysis**:
   - Positive, Neutral, and Negative article counts and percentages.
   - Compound polarity score distribution histogram (-1 to +1).
   - Category-level sentiment composition stacked bar chart.
   - Technical documentation of VADER sentiment scoring rules.

5. **Data Management**:
   - Upload custom CSV datasets with automatic schema validation (`article_id`, `title`, `content`, `source`, `published_at`, `url`).
   - Clean and inspect ingested records.
   - One-click button to trigger the end-to-end Hive pipeline directly from the UI.

6. **System Information**:
   - Live connection status check for Docker Daemon, Hive Container (`hive4`), and HiveServer2 (Port 10000).
   - Database name, table names, storage formats (Delimited TextFile & ORC), and metastore details.
   - Timestamp of last successful pipeline execution.

---

## 7. Running Automated Tests

Run the test suite using `pytest`:

```powershell
pytest tests/ -v
```

### Test Coverage:
- `tests/test_preprocessing.py`: Validates CSV schema validation, text hygiene (removing tabs and carriage returns), deduplication, and handling of malformed records.
- `tests/test_risk_scoring.py`: Validates VADER compound score boundaries, negative intensity conversion, category classification accuracy, severity term extraction, and mathematical risk score calibration.
- `tests/test_pipeline.py`: Validates generated TSV schema, Docker/Hive readiness diagnostics, and output CSV data integrity.

---

## 8. Troubleshooting & FAQ

### 1. Docker daemon connection error: `failed to connect to the docker API at npipe:////./pipe/docker_engine`
- Ensure Docker Desktop is launched on your Windows PC and the whale icon is active in the taskbar notification area.
- Verify in Windows PowerShell: `docker ps`.

### 2. Port 10000 is not reachable
- Wait 30 seconds after starting the container for HiveServer2 to complete its internal startup.
- Check logs inside the container: `docker logs hive4 --tail 50`.

### 3. Missing NLTK `vader_lexicon`
- The pipeline bundles the lexicon in `.venv/nltk_data/sentiment/vader_lexicon.zip`. If running in a fresh environment, run:
  ```powershell
  python -c "import nltk; nltk.download('vader_lexicon')"
  ```
