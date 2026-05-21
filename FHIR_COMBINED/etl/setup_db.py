"""
Run once before ETL: creates llm_ua_ai database, admin/reader users, and full schema.
Usage: python3 etl/setup_db.py
Requires root or a MySQL user with CREATE DATABASE + GRANT privileges.
"""

import sys
import mysql.connector

ROOT_CONN = {
    "host":     "127.0.0.1",
    "port":     3306,
    "user":     "root",
    "password": "P@ssw0rd",
}

DDL = """
CREATE DATABASE IF NOT EXISTS llm_ua_ai
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'llm_ua_admin'@'%' IDENTIFIED BY 'Admin@LLMUA2025!';
CREATE USER IF NOT EXISTS 'llm_ua_reader'@'%' IDENTIFIED BY 'Reader@LLMUA2025!';

GRANT ALL PRIVILEGES ON llm_ua_ai.* TO 'llm_ua_admin'@'%';
GRANT SELECT ON llm_ua_ai.* TO 'llm_ua_reader'@'%';
FLUSH PRIVILEGES;
"""

SCHEMA = """
CREATE TABLE IF NOT EXISTS patients (
  patient_id            VARCHAR(20)  NOT NULL,
  given_name            VARCHAR(255),
  family_name           VARCHAR(255),
  birth_date            DATE,
  gender                ENUM('male','female','other','unknown'),
  street_address        VARCHAR(255),
  city                  VARCHAR(100),
  state                 VARCHAR(20),
  postal_code           VARCHAR(20),
  country               VARCHAR(10)  DEFAULT 'US',
  phone                 VARCHAR(50),
  first_source_hospital VARCHAR(50),
  visited_hospitals     JSON,
  data_sources          JSON,
  filename              VARCHAR(500),
  last_updated          TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (patient_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS observations (
  db_id             INT           NOT NULL AUTO_INCREMENT,
  observation_id    VARCHAR(255)  NOT NULL,
  panel_index       SMALLINT      NOT NULL DEFAULT 0,
  patient_id        VARCHAR(20)   NOT NULL,
  code              VARCHAR(100),
  code_system       VARCHAR(255),
  display           TEXT,
  raw_display       TEXT,
  value_numeric     DECIMAL(20,6),
  value_string      TEXT,
  unit              VARCHAR(50),
  unit_ucum         VARCHAR(50),
  ref_range_low     DECIMAL(12,4),
  ref_range_high    DECIMAL(12,4),
  observation_note  TEXT,
  effective_date    DATE,
  effective_datetime DATETIME,
  status            VARCHAR(20),
  data_type         ENUM('observation','panel_header') DEFAULT 'observation',
  source_type       ENUM('adt','ccda','oru'),
  source_hospital   VARCHAR(50),
  filename          VARCHAR(500),
  created_at        TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (db_id),
  UNIQUE KEY uniq_obs (observation_id, panel_index, source_hospital),
  INDEX idx_obs_patient  (patient_id),
  INDEX idx_obs_code     (code),
  INDEX idx_obs_date     (effective_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS conditions (
  db_id           INT           NOT NULL AUTO_INCREMENT,
  condition_id    VARCHAR(255),
  patient_id      VARCHAR(20)   NOT NULL,
  icd_code        VARCHAR(50),
  display         TEXT,
  raw_display     TEXT,
  code_system     VARCHAR(50),
  raw_fhir_code   TEXT,
  clinical_status VARCHAR(50),
  onset_datetime  DATETIME,
  recorded_date   DATE,
  source_type     ENUM('adt','ccda','oru'),
  source_hospital VARCHAR(50),
  filename        VARCHAR(500),
  created_at      TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (db_id),
  INDEX idx_cond_patient (patient_id),
  INDEX idx_cond_icd     (icd_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS encounters (
  db_id            INT           NOT NULL AUTO_INCREMENT,
  encounter_id     VARCHAR(255),
  patient_id       VARCHAR(20)   NOT NULL,
  status           VARCHAR(20),
  class_code       VARCHAR(50),
  class_display    VARCHAR(100),
  type_code        VARCHAR(100),
  type_display     VARCHAR(255),
  period_start     DATETIME,
  period_end       DATETIME,
  service_provider VARCHAR(255),
  reason_text      TEXT,
  source_type      ENUM('adt','ccda','oru'),
  source_hospital  VARCHAR(50),
  filename         VARCHAR(500),
  created_at       TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (db_id),
  INDEX idx_enc_patient (patient_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS notes (
  db_id           INT           NOT NULL AUTO_INCREMENT,
  patient_id      VARCHAR(20)   NOT NULL,
  note_filename   VARCHAR(500),
  ccda_filename   VARCHAR(500),
  note_date       DATE,
  content         LONGTEXT,
  source_hospital VARCHAR(50),
  created_at      TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (db_id),
  INDEX idx_notes_patient (patient_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ingestion_log (
  id            INT           NOT NULL AUTO_INCREMENT,
  filename      VARCHAR(500)  NOT NULL,
  file_hash     CHAR(64),
  source_type   ENUM('adt','ccda','oru','notes'),
  patient_id    VARCHAR(20),
  rows_loaded   INT           DEFAULT 0,
  rows_skipped  INT           DEFAULT 0,
  processed_at  TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
  status        ENUM('success','partial','failed') NOT NULL,
  error_message TEXT,
  PRIMARY KEY (id),
  UNIQUE KEY uniq_file (filename)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS observation_quarantine (
  id             INT           NOT NULL AUTO_INCREMENT,
  filename       VARCHAR(500),
  patient_id     VARCHAR(20),
  fhir_resource  JSON,
  error_code     VARCHAR(50),
  error_detail   TEXT,
  quarantined_at TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  INDEX idx_quar_patient (patient_id),
  INDEX idx_quar_error   (error_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


def _connect(db=None):
    cfg = dict(ROOT_CONN)
    if db:
        cfg["database"] = db
    return mysql.connector.connect(**cfg)


def run():
    print("Connecting to MySQL...")
    try:
        cx = _connect()
    except mysql.connector.Error as e:
        print(f"ERROR: Cannot connect — {e}")
        print("If you need root access, edit ROOT_CONN in this file.")
        sys.exit(1)

    cur = cx.cursor()

    # Create DB + users (each statement must run separately)
    for stmt in DDL.strip().split(";"):
        stmt = stmt.strip()
        if stmt:
            try:
                cur.execute(stmt)
            except mysql.connector.Error as e:
                # 1396 = user already exists (IF NOT EXISTS should prevent, but just in case)
                if e.errno not in (1396,):
                    print(f"WARN DDL: {e} — stmt: {stmt[:60]}")
    cx.commit()
    cx.close()

    print("Creating schema in llm_ua_ai...")
    cx = _connect(db="llm_ua_ai")
    cur = cx.cursor()
    for stmt in SCHEMA.strip().split(";"):
        stmt = stmt.strip()
        if stmt:
            try:
                cur.execute(stmt)
            except mysql.connector.Error as e:
                print(f"WARN SCHEMA: {e} — stmt: {stmt[:80]}")
    cx.commit()

    # Verify
    cur.execute("SHOW TABLES")
    tables = [r[0] for r in cur.fetchall()]
    print(f"Tables created: {tables}")
    cx.close()
    print("Done. Database llm_ua_ai is ready.")


if __name__ == "__main__":
    run()
