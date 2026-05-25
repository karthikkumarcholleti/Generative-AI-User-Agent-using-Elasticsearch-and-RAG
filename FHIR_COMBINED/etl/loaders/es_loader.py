"""
Elasticsearch bulk indexer for llm_ua_ai ETL.
Triggered once at the end of a complete ETL run — not a polling loop.

Uses the same index name ("patient_data") and document format as the existing
elasticsearch_client.py so the LLM backend can read from it without changes.
"""

import csv
import json
import re
import sys
import os
import mysql.connector
from elasticsearch import Elasticsearch, helpers

# Allow importing from etl/ parent directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from loinc_infer import is_panel_display, infer_panel_subtest, InferenceStats

# ---------------------------------------------------------------------------
# LOINC lookup table — loaded once at import time from the full Loinc.csv
# Provides: clean display names, canonical UCUM units, BM25 search keywords
# ---------------------------------------------------------------------------
_LOINC_REF_PATH = os.path.join(
    os.path.dirname(__file__), "..", "reference_data", "Loinc.csv"
)

# {loinc_code: {"name": str, "ucum": str}}
_LOINC_LOOKUP: dict = {}

def _load_loinc_ref():
    if not os.path.exists(_LOINC_REF_PATH):
        print(f"  WARN: {_LOINC_REF_PATH} not found — display/unit enrichment disabled")
        return
    with open(_LOINC_REF_PATH, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            code = row.get("LOINC_NUM", "").strip().strip('"')
            if not code:
                continue
            long_name = row.get("LONG_COMMON_NAME", "").strip().strip('"')
            # Strip technical qualifiers: "Creatinine [Mass/volume] in Serum or Plasma"
            # → "Creatinine"
            clean = re.sub(r'\s*\[.*', '', long_name).strip()
            clean = re.sub(r'\s+in\s+\S.*', '', clean, flags=re.IGNORECASE).strip()
            if not clean:
                clean = row.get("SHORTNAME", "").strip().strip('"')
            _LOINC_LOOKUP[code] = {
                "name": clean or long_name,
                "ucum": row.get("EXAMPLE_UCUM_UNITS", "").strip().strip('"'),
            }
    print(f"  LOINC ref loaded: {len(_LOINC_LOOKUP):,} codes")

_load_loinc_ref()

# BM25 keyword aliases for common LOINC codes (top clinical labs)
# These are injected into content so "creatinine" matches even if display is cleaned
_LOINC_KEYWORDS: dict = {
    "2160-0":  "creatinine serum kidney function renal",
    "33914-3": "creatinine blood kidney function renal",
    "3094-0":  "bun urea nitrogen blood urea",
    "48642-3": "egfr glomerular filtration kidney function renal",
    "48643-1": "egfr glomerular filtration kidney function renal",
    "2339-0":  "glucose blood sugar fasting diabetes",
    "2345-7":  "glucose blood sugar fasting diabetes",
    "4548-4":  "hba1c hemoglobin a1c glycated hemoglobin diabetes a1c",
    "27353-2": "estimated average glucose eag diabetes",
    "718-7":   "hemoglobin hgb hb anemia cbc blood count",
    "786-4":   "hematocrit hct packed cell volume cbc",
    "6690-2":  "wbc white blood cell leukocyte count cbc infection",
    "789-8":   "rbc red blood cell erythrocyte count cbc",
    "777-3":   "platelet plt thrombocyte count cbc",
    "787-2":   "mcv mean corpuscular volume cbc anemia",
    "2951-2":  "sodium na electrolyte hyponatremia hypernatremia",
    "5902-2":  "sodium na electrolyte serum",
    "2823-3":  "potassium k electrolyte hypokalemia hyperkalemia",
    "2075-0":  "chloride cl electrolyte",
    "2028-9":  "bicarbonate co2 carbon dioxide acid base",
    "17861-6": "calcium ca electrolyte hypercalcemia hypocalcemia",
    "19123-9": "magnesium mg electrolyte",
    "2777-1":  "phosphate phosphorus electrolyte",
    "1751-7":  "albumin protein liver nutritional",
    "1975-2":  "bilirubin liver function jaundice",
    "1920-8":  "ast sgot aspartate aminotransferase liver function",
    "1742-6":  "alt sgpt alanine aminotransferase liver function",
    "6768-6":  "alkaline phosphatase alp alk phos liver function",
    "2093-3":  "cholesterol total lipid panel cardiovascular",
    "2085-9":  "hdl cholesterol high density lipoprotein lipid",
    "2089-1":  "ldl cholesterol low density lipoprotein lipid",
    "2571-8":  "triglycerides lipid panel cardiovascular",
    "10839-9": "troponin i cardiac troponin heart attack mi acs",
    "33762-6": "bnp proBNP natriuretic peptide heart failure",
    "1988-5":  "crp c reactive protein inflammation",
    "11579-0": "tsh thyroid stimulating hormone thyroid function",
    "3024-7":  "free t4 thyroxine thyroid function",
    "8480-6":  "systolic blood pressure sbp bp hypertension vital",
    "8462-4":  "diastolic blood pressure dbp bp hypertension vital",
    "8867-4":  "heart rate pulse hr tachycardia bradycardia vital",
    "9279-1":  "respiratory rate respiration breathing vital",
    "2708-6":  "oxygen saturation spo2 o2 sat hypoxia vital",
    "59408-5": "oxygen saturation spo2 pulse oximetry vital",
    "8310-5":  "body temperature temp fever vital",
    "29463-7": "body weight kg weight vital",
    "8302-2":  "body height cm height vital",
    "39156-5": "bmi body mass index obesity vital",
}

# SNOMED semantic tag pattern — strip these from condition display
_SNOMED_SUFFIX = re.compile(
    r'\s*\((?:disorder|finding|situation|observable entity|procedure|'
    r'body structure|qualifier value)\)\s*$',
    re.IGNORECASE
)

ES_HOST = "http://localhost:9200"
INDEX   = "patient_data"  # replace old index — backend hardcodes this name throughout

DB_CONFIG = {
    "host":     "127.0.0.1",
    "port":     3306,
    "user":     "llm_ua_admin",
    "password": "P@ssw0rd",
    "database": "llm_ua_enterprise",
    "charset":  "utf8mb4",
}

_INDEX_SETTINGS = {
    "settings": {
        "number_of_shards":   1,
        "number_of_replicas": 0,
    },
    "mappings": {
        "properties": {
            "enterprise_patient_id": {"type": "keyword"},
            "data_type":       {"type": "keyword"},
            "source_hospital": {"type": "keyword"},
            "source_type":     {"type": "keyword"},
            "code":            {"type": "keyword"},
            "effective_date":  {"type": "date", "format": "yyyy-MM-dd||strict_date_optional_time"},
            "content":         {"type": "text", "analyzer": "english"},
            "embedding":       {"type": "dense_vector", "dims": 384, "index": True, "similarity": "cosine"},
        }
    },
}


def bulk_index_all(verbose: bool = True):
    es = Elasticsearch(ES_HOST, request_timeout=60)
    if not es.ping():
        raise RuntimeError(f"Cannot connect to Elasticsearch at {ES_HOST}")

    # Recreate index fresh
    if es.indices.exists(index=INDEX):
        es.indices.delete(index=INDEX)
        if verbose:
            print(f"  Deleted existing ES index '{INDEX}'")
    es.indices.create(index=INDEX, body=_INDEX_SETTINGS)
    if verbose:
        print(f"  Created ES index '{INDEX}'")

    cx = mysql.connector.connect(**DB_CONFIG)

    counts = {"observations": 0, "conditions": 0, "encounters": 0, "notes": 0}
    infer_stats = InferenceStats()

    # Stream observations with inference statistics
    n = 0
    for ok, info in helpers.parallel_bulk(
        es, _obs_actions(cx, infer_stats), chunk_size=500, thread_count=2
    ):
        if not ok:
            print(f"  WARN ES: {info}")
        n += 1
    counts["observations"] = n
    if verbose:
        print(f"  Indexed {n:,} observations")

    # Stream remaining tables
    for table, gen_fn in [
        ("conditions", _cond_actions),
        ("encounters", _enc_actions),
        ("notes",      _note_actions),
    ]:
        n = 0
        for ok, info in helpers.parallel_bulk(es, gen_fn(cx), chunk_size=500, thread_count=2):
            if not ok:
                print(f"  WARN ES: {info}")
            n += 1
        counts[table] = n
        if verbose:
            print(f"  Indexed {n:,} {table}")

    cx.close()
    if verbose:
        print(f"  ES indexing complete: {counts}")
        print(f"\n  {infer_stats.report()}")
    return counts, infer_stats


# ---------------------------------------------------------------------------
# Per-table action generators
# ---------------------------------------------------------------------------

def _clean_display(code: str, raw: str) -> str:
    """Return the most human-readable display name for a LOINC code."""
    if code and code in _LOINC_LOOKUP:
        name = _LOINC_LOOKUP[code].get("name", "").strip()
        if name:
            return name
    if raw and ":" in raw:
        # Fallback: use first colon-delimited component, title-cased
        _KEEP_UPPER = {"BUN", "HDL", "LDL", "WBC", "RBC", "TSH", "ALT", "AST",
                       "ALK", "ALP", "CRP", "BNP", "INR", "PTT", "HIV", "HCV",
                       "HBV", "PSA", "CEA", "AFP", "LDH", "CK", "GFR", "ACE",
                       "CBC", "CMP", "BMP"}
        component = raw.split(":")[0].strip()
        words = component.split()
        return " ".join(w.upper() if w.upper() in _KEEP_UPPER else w.capitalize() for w in words)
    return raw or ""


def _canonical_unit(code: str, raw_unit: str) -> str:
    """Return canonical UCUM unit: prefer unit_ucum from MySQL, fall back to LOINC ref."""
    if raw_unit and raw_unit not in ("unit", ""):
        return raw_unit
    if code and code in _LOINC_LOOKUP:
        ucum = _LOINC_LOOKUP[code].get("ucum", "").strip()
        if ucum:
            return ucum
    return ""


def _obs_actions(cx, stats: "InferenceStats | None" = None):
    cur = cx.cursor(dictionary=True)
    cur.execute(
        """
        SELECT o.*, p.given_name, p.family_name, p.birth_date
        FROM observations o
        LEFT JOIN patients p ON o.enterprise_patient_id = p.enterprise_patient_id
        """
    )
    for row in cur:
        raw_display = row.get("display") or row.get("raw_display") or ""
        code        = row.get("code") or ""

        # Enrich panel sub-tests: declarative ref-range inference
        if is_panel_display(raw_display):
            ref_lo  = float(row["ref_range_low"])  if row.get("ref_range_low")  is not None else None
            ref_hi  = float(row["ref_range_high"]) if row.get("ref_range_high") is not None else None
            val_num = float(row["value_numeric"])  if row.get("value_numeric")  is not None else None
            result  = infer_panel_subtest(row.get("unit"), ref_lo, ref_hi, val_num)
            if stats:
                stats.record(result)
            if result:
                raw_display = result.display_name
                code        = result.loinc_code or code

        # Use cleaner display from LOINC lookup
        display = _clean_display(code, raw_display)

        # Canonical unit: prefer MySQL unit_ucum, fall back to LOINC ref
        unit_ucum = row.get("unit_ucum") or ""
        unit_raw  = row.get("unit") or ""
        best_unit = _canonical_unit(code, unit_ucum or unit_raw)

        content_parts = []
        if display:
            content_parts.append(display)
        # Keep original panel header so BM25 still matches "CMP" / "BMP" queries
        orig_raw = row.get("display") or ""
        if orig_raw and orig_raw != display and orig_raw != raw_display:
            content_parts.append(orig_raw)
        if row.get("raw_display") and row["raw_display"] not in (display, raw_display, orig_raw):
            content_parts.append(row["raw_display"])
        # BM25 alias keywords for this LOINC code
        if code and code in _LOINC_KEYWORDS:
            content_parts.append(_LOINC_KEYWORDS[code])
        # Numeric value + unit
        if row.get("value_numeric") is not None:
            val_str = f"{row['value_numeric']} {best_unit}".strip()
            content_parts.append(val_str)
        if row.get("value_string"):
            content_parts.append(row["value_string"])
        if row.get("observation_note"):
            content_parts.append(row["observation_note"])

        yield {
            "_index": INDEX,
            "_id":    f"obs_{row['db_id']}",
            "_source": {
                "enterprise_patient_id": row["enterprise_patient_id"],
                "data_type":        "observation",
                "source_type":      row.get("source_type"),
                "source_hospital":  row.get("source_hospital"),
                "code":             code,
                "display":          display,
                "value_numeric":    float(row["value_numeric"]) if row.get("value_numeric") else None,
                "value_string":     row.get("value_string"),
                "unit":             best_unit or unit_raw,
                "unit_ucum":        unit_ucum,
                "ref_range_low":    float(row["ref_range_low"]) if row.get("ref_range_low") else None,
                "ref_range_high":   float(row["ref_range_high"]) if row.get("ref_range_high") else None,
                "effective_date":   str(row["effective_date"]) if row.get("effective_date") else None,
                "effective_datetime": str(row["effective_datetime"]) if row.get("effective_datetime") else None,
                "obs_data_type":    row.get("data_type"),
                "patient_name":     f"{row.get('given_name','')} {row.get('family_name','')}".strip(),
                "content":          " | ".join(content_parts),
            },
        }
    cur.close()


def _cond_actions(cx):
    cur = cx.cursor(dictionary=True)
    cur.execute("SELECT * FROM conditions")
    for row in cur:
        raw = row.get("display") or row.get("raw_display") or row.get("icd_code") or ""
        # Strip SNOMED semantic tags: "(disorder)", "(finding)", "(situation)", etc.
        display = _SNOMED_SUFFIX.sub("", raw).strip() or raw
        yield {
            "_index": INDEX,
            "_id":    f"cond_{row['db_id']}",
            "_source": {
                "enterprise_patient_id": row["enterprise_patient_id"],
                "data_type":       "condition",
                "source_type":     row.get("source_type"),
                "source_hospital": row.get("source_hospital"),
                "icd_code":        row.get("icd_code"),
                "display":         display,           # was missing — backend reads this
                "clinical_status": row.get("clinical_status"),
                "onset_datetime":  str(row["onset_datetime"]) if row.get("onset_datetime") else None,
                "effective_date":  str(row["recorded_date"]) if row.get("recorded_date") else None,
                "content":         display,
            },
        }
    cur.close()


def _enc_actions(cx):
    cur = cx.cursor(dictionary=True)
    cur.execute("SELECT * FROM encounters")
    for row in cur:
        parts = []
        if row.get("class_display"):
            parts.append(row["class_display"])
        if row.get("type_display"):
            parts.append(row["type_display"])
        if row.get("reason_text"):
            parts.append(row["reason_text"])
        yield {
            "_index": INDEX,
            "_id":    f"enc_{row['db_id']}",
            "_source": {
                "enterprise_patient_id": row["enterprise_patient_id"],
                "data_type":       "encounter",
                "source_type":     row.get("source_type"),
                "source_hospital": row.get("source_hospital"),
                "class_code":      row.get("class_code"),
                "effective_date":  str(row["period_start"])[:10] if row.get("period_start") else None,
                "content":         " | ".join(parts),
            },
        }
    cur.close()


def _note_actions(cx):
    cur = cx.cursor(dictionary=True)
    cur.execute("SELECT * FROM notes")
    for row in cur:
        yield {
            "_index": INDEX,
            "_id":    f"note_{row['db_id']}",
            "_source": {
                "enterprise_patient_id": row["enterprise_patient_id"],
                "data_type":       "note",
                "source_hospital": row.get("source_hospital"),
                "note_date":       str(row["note_date"]) if row.get("note_date") else None,
                "effective_date":  str(row["note_date"]) if row.get("note_date") else None,
                "content":         row.get("content") or "",
            },
        }
    cur.close()


if __name__ == "__main__":
    bulk_index_all(verbose=True)
