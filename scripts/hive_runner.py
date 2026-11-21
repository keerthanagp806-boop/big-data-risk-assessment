"""Apache Hive execution and orchestration module via Docker and Beeline."""

import sys
import subprocess
import time
import socket
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from utils.config import (
    HIVE_CONTAINER,
    HIVE_HOST,
    HIVE_PORT,
    HIVE_HTTP_PORT,
    HIVE_DATABASE,
    HIVE_USER,
    HIVE_PASSWORD,
    PROCESSED_DATA_PATH,
    OUTPUTS_DIR,
    HIVE_DIR
)
from utils.logger import logger

class HiveRunner:
    """Manages Docker Apache Hive 4.0.0 lifecycle, Beeline queries, and analytical exports."""

    def __init__(
        self,
        container_name: str = HIVE_CONTAINER,
        host: str = HIVE_HOST,
        port: int = HIVE_PORT,
        database: str = HIVE_DATABASE,
        user: str = HIVE_USER,
        password: str = HIVE_PASSWORD
    ):
        self.container = container_name
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.jdbc_url = f"jdbc:hive2://localhost:{self.port}/default"

    def check_docker_available(self) -> Tuple[bool, str]:
        """Verifies if docker CLI is present and the Docker daemon is responding."""
        try:
            res = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if res.returncode == 0:
                return True, "Docker daemon is running."
            return False, f"Docker daemon is not responsive: {res.stderr.strip() or res.stdout.strip()}"
        except FileNotFoundError:
            return False, "Docker CLI is not installed or not in PATH."
        except Exception as e:
            return False, f"Docker check encountered error: {str(e)}"

    def check_container_status(self) -> Tuple[bool, str]:
        """Checks if the Hive 4 container is running."""
        try:
            res = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Status}}", self.container],
                capture_output=True,
                text=True,
                timeout=5
            )
            status = res.stdout.strip()
            if status == "running":
                return True, f"Container '{self.container}' is running."
            elif status:
                return False, f"Container '{self.container}' exists but is '{status}'."
            return False, f"Container '{self.container}' not found."
        except Exception as e:
            return False, f"Error checking container status: {str(e)}"

    def check_hiveserver2_port(self, timeout_sec: int = 3) -> bool:
        """Probes whether the HiveServer2 TCP port is listening."""
        try:
            with socket.create_connection((self.host, self.port), timeout=timeout_sec):
                return True
        except (socket.timeout, ConnectionRefException, ConnectionResetError, OSError):
            return False

    def check_hive_ready(self, retries: int = 5, delay_sec: int = 3) -> Tuple[bool, str]:
        """Checks if HiveServer2 is ready to accept Beeline connections."""
        if not self.check_hiveserver2_port():
            return False, f"Port {self.port} is not reachable on host '{self.host}'."

        test_cmd = [
            "docker", "exec", self.container,
            "/opt/hive/bin/beeline",
            "-u", self.jdbc_url,
            "-n", self.user,
            "-p", self.password,
            "-e", "SHOW DATABASES;"
        ]

        for attempt in range(1, retries + 1):
            try:
                res = subprocess.run(test_cmd, capture_output=True, text=True, timeout=25)
                if res.returncode == 0:
                    return True, "HiveServer2 is accepting Beeline queries."
                logger.info(f"Waiting for HiveServer2 ready state (attempt {attempt}/{retries})...")
                time.sleep(delay_sec)
            except subprocess.TimeoutExpired:
                logger.warning(f"Beeline query timed out on attempt {attempt}.")
                time.sleep(delay_sec)
            except Exception as e:
                return False, f"Hive readiness test error: {e}"

        return False, "HiveServer2 did not respond within the retry period."

    def ensure_container_started(self) -> Tuple[bool, str]:
        """Starts the existing container or creates a new one if missing."""
        docker_ok, docker_msg = self.check_docker_available()
        if not docker_ok:
            return False, docker_msg

        is_running, status_msg = self.check_container_status()
        if is_running:
            return True, status_msg

        # Check if container exists in stopped state
        res = subprocess.run(
            ["docker", "ps", "-a", "--filter", f"name={self.container}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )
        if self.container in res.stdout:
            logger.info(f"Starting stopped container '{self.container}'...")
            start_res = subprocess.run(["docker", "start", self.container], capture_output=True, text=True)
            if start_res.returncode == 0:
                return True, f"Container '{self.container}' started successfully."
            return False, f"Failed to start container: {start_res.stderr.strip()}"

        # Otherwise create container
        logger.info(f"Container '{self.container}' not found. Creating container with apache/hive:4.0.0...")
        # Create volume if needed
        subprocess.run(["docker", "volume", "create", "hive_warehouse"], capture_output=True)

        create_cmd = [
            "docker", "run", "-d",
            "--name", self.container,
            "-p", f"{self.port}:10000",
            "-p", f"{HIVE_HTTP_PORT}:10002",
            "-v", "hive_warehouse:/opt/hive/data/warehouse",
            "--env", "SERVICE_NAME=hiveserver2",
            "apache/hive:4.0.0"
        ]
        create_res = subprocess.run(create_cmd, capture_output=True, text=True)
        if create_res.returncode == 0:
            logger.info("Hive container created. Waiting for HiveServer2 initialization (approx 30s)...")
            return True, f"Hive container '{self.container}' created and started."
        return False, f"Failed to create Hive container: {create_res.stderr.strip()}"

    def copy_file_to_container(self, local_path: Path, container_path: str) -> bool:
        """Copies a local file into the Hive Docker container."""
        if not local_path.exists():
            logger.error(f"Cannot copy non-existent local file: {local_path}")
            return False

        # Ensure container destination directory exists
        dest_dir = str(Path(container_path).parent).replace("\\", "/")
        subprocess.run(
            ["docker", "exec", self.container, "mkdir", "-p", dest_dir],
            capture_output=True
        )

        res = subprocess.run(
            ["docker", "cp", str(local_path), f"{self.container}:{container_path}"],
            capture_output=True,
            text=True
        )
        if res.returncode == 0:
            logger.info(f"Copied {local_path} to {self.container}:{container_path}")
            return True
        logger.error(f"docker cp failed: {res.stderr.strip()}")
        return False

    def execute_beeline_query(self, query: str, output_csv: Optional[Path] = None) -> Tuple[bool, str]:
        """
        Executes a HiveQL query via Beeline in the container.
        Optionally parses and saves the output to a CSV file.
        """
        cmd = [
            "docker", "exec", self.container,
            "/opt/hive/bin/beeline",
            "-u", self.jdbc_url,
            "-n", self.user,
            "-p", self.password,
            "--outputformat=csv2",
            "--showHeader=true",
            "-e", query
        ]

        res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if res.returncode != 0:
            err = res.stderr.strip() or res.stdout.strip()
            logger.error(f"HiveQL query failed: {err}")
            return False, err

        output = res.stdout.strip()

        # If saving to CSV, clean up any beeline banner lines and write
        if output_csv:
            output_csv.parent.mkdir(parents=True, exist_ok=True)
            lines = output.splitlines()
            # Filter out Beeline info lines (e.g. Connecting to..., Connected to...)
            csv_lines = [
                line for line in lines
                if not line.startswith("Connecting to")
                and not line.startswith("Connected to")
                and not line.startswith("INFO ")
                and not line.startswith("WARN ")
                and not line.startswith("SLF4J:")
                and not line.startswith("Transaction isolation:")
            ]
            clean_content = "\n".join(csv_lines).strip()
            with open(output_csv, "w", encoding="utf-8") as f:
                f.write(clean_content + "\n")
            logger.info(f"Saved query result to {output_csv}")

        return True, output

    def execute_beeline_script(self, script_path: Path) -> Tuple[bool, str]:
        """Copies an SQL script into the container and executes it via Beeline."""
        if not script_path.exists():
            return False, f"SQL script not found: {script_path}"

        container_script_path = f"/tmp/{script_path.name}"
        if not self.copy_file_to_container(script_path, container_script_path):
            return False, f"Failed to transfer script {script_path.name} to container."

        cmd = [
            "docker", "exec", self.container,
            "/opt/hive/bin/beeline",
            "-u", self.jdbc_url,
            "-n", self.user,
            "-p", self.password,
            "-f", container_script_path
        ]

        logger.info(f"Executing HiveQL script: {script_path.name}...")
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if res.returncode != 0:
            err = res.stderr.strip() or res.stdout.strip()
            logger.error(f"Script {script_path.name} execution failed: {err}")
            return False, err

        logger.info(f"Script {script_path.name} completed successfully.")
        return True, res.stdout

    def run_full_hive_pipeline(self) -> Tuple[bool, str]:
        """
        Executes the end-to-end Hive analytics workflow:
        1. Verify Docker & HiveServer2
        2. Transfer preprocessed TSV
        3. Create tables (news_raw)
        4. Load data into news_raw
        5. Execute risk assessment (assessed_news ORC CTAS)
        6. Execute analytical queries and export to outputs/
        """
        logger.info("==================================================")
        logger.info("STARTING APACHE HIVE 4.0.0 PIPELINE EXECUTION")
        logger.info("==================================================")

        # Step 1: Check Docker
        docker_ok, docker_msg = self.check_docker_available()
        if not docker_ok:
            return False, f"Docker requirement failed: {docker_msg}"

        # Step 2: Ensure Hive container is up
        started, start_msg = self.ensure_container_started()
        if not started:
            return False, f"Hive container initialization failed: {start_msg}"

        # Step 3: Wait for HiveServer2
        ready, ready_msg = self.check_hive_ready(retries=10, delay_sec=5)
        if not ready:
            return False, f"HiveServer2 connection failed: {ready_msg}"

        # Step 4: Transfer TSV dataset into container
        if not PROCESSED_DATA_PATH.exists():
            return False, f"Processed dataset missing at: {PROCESSED_DATA_PATH}"

        container_tsv = "/opt/hive/data/news_enriched.tsv"
        if not self.copy_file_to_container(PROCESSED_DATA_PATH, container_tsv):
            return False, "Failed to copy dataset into Hive container."

        # Step 5: Execute 01_create_tables.sql
        script1 = HIVE_DIR / "01_create_tables.sql"
        ok1, out1 = self.execute_beeline_script(script1)
        if not ok1:
            return False, f"Table creation failed: {out1}"

        # Step 6: Load TSV data into news_raw
        load_query = f"USE {self.database}; LOAD DATA LOCAL INPATH '{container_tsv}' OVERWRITE INTO TABLE news_raw;"
        logger.info("Loading TSV data into table 'news_raw'...")
        ok_load, out_load = self.execute_beeline_query(load_query)
        if not ok_load:
            return False, f"Failed to load data into news_raw: {out_load}"

        # Step 7: Execute 02_risk_analysis.sql (CTAS with ORC)
        script2 = HIVE_DIR / "02_risk_analysis.sql"
        ok2, out2 = self.execute_beeline_script(script2)
        if not ok2:
            return False, f"Hive risk assessment CTAS failed: {out2}"

        # Step 8: Execute analytics and export to CSVs
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        logger.info("Exporting HiveQL analytics to CSV output files...")

        export_queries = {
            "risk_summary.csv": f"""
                USE {self.database};
                SELECT risk_level, COUNT(*) AS article_count,
                       ROUND(AVG(risk_score), 2) AS avg_risk_score,
                       ROUND(AVG(negative_intensity), 2) AS avg_negative_intensity,
                       ROUND(AVG(severity_score), 2) AS avg_severity_score
                FROM assessed_news
                GROUP BY risk_level
                ORDER BY avg_risk_score DESC;
            """,
            "category_summary.csv": f"""
                USE {self.database};
                SELECT category, COUNT(*) AS total_articles,
                       ROUND(AVG(risk_score), 2) AS avg_risk_score,
                       ROUND(AVG(severity_score), 2) AS avg_severity_score,
                       SUM(CASE WHEN risk_level = 'HIGH' THEN 1 ELSE 0 END) AS high_risk_count,
                       SUM(CASE WHEN risk_level = 'MEDIUM' THEN 1 ELSE 0 END) AS medium_risk_count,
                       SUM(CASE WHEN risk_level = 'LOW' THEN 1 ELSE 0 END) AS low_risk_count
                FROM assessed_news
                GROUP BY category
                ORDER BY avg_risk_score DESC;
            """,
            "source_summary.csv": f"""
                USE {self.database};
                SELECT source, COUNT(*) AS total_articles,
                       ROUND(AVG(risk_score), 2) AS avg_risk_score,
                       SUM(CASE WHEN risk_level = 'HIGH' THEN 1 ELSE 0 END) AS high_risk_count,
                       ROUND(AVG(sentiment_compound), 4) AS avg_sentiment_compound
                FROM assessed_news
                GROUP BY source
                ORDER BY total_articles DESC, avg_risk_score DESC;
            """,
            "sentiment_summary.csv": f"""
                USE {self.database};
                SELECT sentiment_label, COUNT(*) AS article_count,
                       ROUND(AVG(sentiment_compound), 4) AS avg_compound,
                       ROUND(AVG(risk_score), 2) AS avg_risk_score
                FROM assessed_news
                GROUP BY sentiment_label
                ORDER BY article_count DESC;
            """,
            "trend_summary.csv": f"""
                USE {self.database};
                SELECT SUBSTR(published_at, 1, 10) AS publication_date,
                       COUNT(*) AS article_count,
                       ROUND(AVG(risk_score), 2) AS avg_risk_score,
                       SUM(CASE WHEN risk_level = 'HIGH' THEN 1 ELSE 0 END) AS high_risk_count
                FROM assessed_news
                GROUP BY SUBSTR(published_at, 1, 10)
                ORDER BY publication_date ASC;
            """,
            "news_records.csv": f"""
                USE {self.database};
                SELECT article_id, title, content, source, published_at, url,
                       category, sentiment_label, sentiment_compound,
                       negative_intensity, severity_score, severity_keywords,
                       risk_score, risk_level
                FROM assessed_news
                ORDER BY risk_score DESC;
            """
        }

        for filename, qry in export_queries.items():
            csv_path = OUTPUTS_DIR / filename
            ok_exp, out_exp = self.execute_beeline_query(qry, output_csv=csv_path)
            if not ok_exp:
                return False, f"Failed exporting {filename}: {out_exp}"

        logger.info("Hive pipeline completed successfully. All outputs exported.")
        return True, "Hive pipeline executed and analytical summaries exported."
