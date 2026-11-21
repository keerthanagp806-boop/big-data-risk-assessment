"""Configuration module for Big Data Risk Assessment Platform."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Directory paths
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
OUTPUTS_DIR = BASE_DIR / "outputs"
HIVE_DIR = BASE_DIR / "hive"
SCRIPTS_DIR = BASE_DIR / "scripts"

# Default file paths
RAW_DATA_PATH = Path(os.getenv("RAW_DATA_PATH", str(RAW_DATA_DIR / "news.csv")))
PROCESSED_DATA_PATH = Path(os.getenv("PROCESSED_DATA_PATH", str(PROCESSED_DATA_DIR / "news_enriched.tsv")))

# Apache Hive configuration
HIVE_HOST = os.getenv("HIVE_HOST", "localhost")
HIVE_PORT = int(os.getenv("HIVE_PORT", 10000))
HIVE_HTTP_PORT = int(os.getenv("HIVE_SERVER2_HTTP_PORT", 10002))
HIVE_DATABASE = os.getenv("HIVE_DATABASE", "news_risk")
HIVE_CONTAINER = os.getenv("HIVE_DOCKER_CONTAINER", "hive4")
HIVE_USER = os.getenv("HIVE_USER", "anonymous")
HIVE_PASSWORD = os.getenv("HIVE_PASSWORD", "anonymous")

# Risk Assessment Model Parameters
RISK_NEGATIVE_WEIGHT = float(os.getenv("RISK_NEGATIVE_WEIGHT", 0.60))
RISK_SEVERITY_WEIGHT = float(os.getenv("RISK_SEVERITY_WEIGHT", 0.40))
RISK_LOW_THRESHOLD = float(os.getenv("RISK_LOW_THRESHOLD", 40.0))
RISK_HIGH_THRESHOLD = float(os.getenv("RISK_HIGH_THRESHOLD", 75.0))

# Category Keyword Dictionaries
CATEGORY_KEYWORDS = {
    "Politics": [
        "election", "vote", "parliament", "congress", "senate", "president", "minister",
        "legislation", "diplomat", "government", "policy", "campaign", "democracy",
        "opposition", "treaty", "ambassador", "sanction", "impeachment"
    ],
    "Economy": [
        "market", "inflation", "gdp", "stock", "trade", "tariff", "interest rate",
        "banking", "recession", "currency", "employment", "fiscal", "debt",
        "investment", "economic", "wall street", "central bank", "deficit"
    ],
    "Security": [
        "military", "defense", "cyberattack", "terrorism", "conflict", "war", "hostage",
        "missile", "intelligence", "police", "surveillance", "weapon", "border",
        "threat", "assault", "bombing", "extremist", "security force"
    ],
    "Health": [
        "virus", "hospital", "outbreak", "vaccine", "disease", "pandemic", "epidemic",
        "healthcare", "medical", "infection", "doctor", "clinical", "pharmaceutical",
        "public health", "mortality", "treatment", "fda", "who"
    ],
    "Environment": [
        "climate", "flood", "earthquake", "wildfire", "hurricane", "drought",
        "emission", "carbon", "renewable", "pollution", "biodiversity", "tsunami",
        "cyclone", "global warming", "ecological", "conservation"
    ],
    "Technology": [
        "artificial intelligence", "ai", "software", "hardware", "semiconductor",
        "cloud computing", "algorithm", "robotics", "quantum", "machine learning",
        "innovation", "tech giant", "telecom", "startup", "biotech"
    ]
}

# Severity Keyword Dictionaries with weights (1-10 scale)
SEVERITY_KEYWORDS = {
    # Catastrophic / High danger (Weight: 9-10)
    "terrorism": 10,
    "terrorist": 10,
    "bombing": 10,
    "mass casualty": 10,
    "nuclear strike": 10,
    "war": 9,
    "hostage": 9,
    "cyberattack": 9,
    "ransomware": 8,
    "missile strike": 9,
    "biological weapon": 10,
    "chemical attack": 10,
    
    # Severe threats & emergencies (Weight: 7-8)
    "conflict": 8,
    "violence": 8,
    "assault": 7,
    "lethal": 8,
    "pandemic": 8,
    "deadly outbreak": 8,
    "fatalities": 8,
    "death toll": 8,
    "evacuation": 7,
    "tsunami": 8,
    "earthquake": 8,
    "hurricane": 7,
    "wildfire": 7,
    "devastating": 7,
    "critical vulnerability": 8,
    "financial collapse": 8,
    "banking crisis": 8,
    "infrastructure failure": 8,

    # Moderate concern / Tension (Weight: 5-6)
    "threat": 6,
    "crisis": 6,
    "clash": 6,
    "strike": 5,
    "emergency": 6,
    "disaster": 6,
    "recession": 6,
    "default": 6,
    "collapse": 6,
    "breach": 6,
    "epidemic": 6,
    "lockdown": 5,
    "catastrophe": 6,
    "sanctions": 5,
    "investigation": 4,
    "warning": 4,
    "alert": 4
}
