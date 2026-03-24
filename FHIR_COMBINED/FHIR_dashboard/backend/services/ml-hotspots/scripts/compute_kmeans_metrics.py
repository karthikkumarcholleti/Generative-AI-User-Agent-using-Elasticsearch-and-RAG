import json
import math
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, KMeans
from sklearn.metrics import davies_bouldin_score, silhouette_score
from sklearn.preprocessing import StandardScaler


def prepare_cdc_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    prepared = df.copy()
    prepared["date"] = pd.to_datetime(
        prepared["Year"].astype(str) + "-" + prepared["Week"].astype(str) + "-1",
        format="%Y-%W-%w",
    )
    prepared["cases_per_100k"] = (prepared["Cases"] / prepared["Population"]) * 100_000
    prepared = prepared.sort_values("date")
    prepared["growth_rate"] = prepared["Cases"].diff().fillna(0)
    feature_cols = ["Latitude", "Longitude", "cases_per_100k", "growth_rate"]
    return prepared.dropna(subset=feature_cols), feature_cols


def choose_k(n_samples: int) -> int:
    estimated = int(math.sqrt(max(n_samples, 1) / 2))
    return max(10, min(estimated, 60))


def safe_float(value):
    if value is None:
        return None
    try:
        float_value = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(float_value) or math.isinf(float_value):
        return None
    return float_value


def summarize_cdc_metrics(cdc_df: pd.DataFrame) -> dict:
    cdc_prepared, feature_columns = prepare_cdc_features(cdc_df)
    scaler = StandardScaler()
    X_cdc = scaler.fit_transform(cdc_prepared[feature_columns])

    dbscan_model = DBSCAN(eps=0.3, min_samples=3)
    dbscan_labels = dbscan_model.fit_predict(X_cdc)
    cdc_prepared["cluster_dbscan"] = dbscan_labels
    cdc_prepared["is_hotspot_dbscan"] = dbscan_labels != -1

    n_clusters_dbscan = len(set(dbscan_labels)) - (1 if -1 in dbscan_labels else 0)
    hotspot_records_dbscan = int(cdc_prepared["is_hotspot_dbscan"].sum())
    hotspot_ratio_dbscan = safe_float(hotspot_records_dbscan / len(cdc_prepared))

    if n_clusters_dbscan > 1:
        mask = dbscan_labels != -1
        sil_dbscan = safe_float(silhouette_score(X_cdc[mask], dbscan_labels[mask]))
        db_dbscan = safe_float(davies_bouldin_score(X_cdc[mask], dbscan_labels[mask]))
    else:
        sil_dbscan = None
        db_dbscan = None

    k = choose_k(len(cdc_prepared))
    kmeans_model = KMeans(n_clusters=k, random_state=42, n_init=10)
    kmeans_labels = kmeans_model.fit_predict(X_cdc)
    cdc_prepared["cluster_kmeans"] = kmeans_labels

    intensity = (
        cdc_prepared.groupby("cluster_kmeans")["cases_per_100k"].mean().rename("mean_cases_per_100k")
    )
    threshold = float(intensity.quantile(0.80))
    intensity_lookup = intensity.to_dict()
    cdc_prepared["cluster_intensity"] = cdc_prepared["cluster_kmeans"].map(intensity_lookup)
    cdc_prepared["is_hotspot_kmeans"] = cdc_prepared["cluster_intensity"] >= threshold

    hotspot_records_kmeans = int(cdc_prepared["is_hotspot_kmeans"].sum())
    hotspot_ratio_kmeans = safe_float(cdc_prepared["is_hotspot_kmeans"].mean())
    sil_kmeans = safe_float(silhouette_score(X_cdc, kmeans_labels))
    db_kmeans = safe_float(davies_bouldin_score(X_cdc, kmeans_labels))

    return {
        "dbscan": {
            "cluster_count": int(n_clusters_dbscan),
            "hotspot_records": hotspot_records_dbscan,
            "hotspot_ratio": hotspot_ratio_dbscan,
            "silhouette": sil_dbscan,
            "davies_bouldin": db_dbscan,
            "total_records": int(len(cdc_prepared)),
            "eps": 0.3,
            "min_samples": 3,
        },
        "kmeans": {
            "cluster_count": int(k),
            "hotspot_records": hotspot_records_kmeans,
            "hotspot_ratio": hotspot_ratio_kmeans,
            "silhouette": sil_kmeans,
            "davies_bouldin": db_kmeans,
            "total_records": int(len(cdc_prepared)),
            "threshold_quantile": 0.80,
        },
    }


def summarize_fhir_metrics(fhir_df: pd.DataFrame) -> dict:
    candidate_columns = [
        "latitude",
        "longitude",
        "total_cases",
        "cases_per_disease",
        "category_percentage",
        "category_percentage.1",
        "growth_rate",
    ]
    available_columns = [col for col in candidate_columns if col in fhir_df.columns]

    if len(available_columns) < 4:
        return {"available": False, "reason": "insufficient_feature_columns"}

    feature_columns = available_columns[:4]
    scaler = StandardScaler()
    X_fhir = scaler.fit_transform(fhir_df[feature_columns].fillna(0))

    dbscan_model = DBSCAN(eps=0.5, min_samples=5)
    db_labels = dbscan_model.fit_predict(X_fhir)
    kmeans_model = KMeans(n_clusters=choose_k(len(fhir_df)), random_state=42, n_init=10)
    km_labels = kmeans_model.fit_predict(X_fhir)

    hotspot_ratio_dbscan = safe_float(np.mean(db_labels != -1))
    intensity = (
        pd.DataFrame({"cluster": km_labels, "total_cases": fhir_df["total_cases"]})
        .groupby("cluster")["total_cases"].mean()
    )
    threshold = float(intensity.quantile(0.80))
    hotspot_ratio_kmeans = safe_float(
        np.mean([intensity[label] >= threshold for label in km_labels])
    )

    return {
        "available": True,
        "records": int(len(fhir_df)),
        "dbscan_hotspot_ratio": hotspot_ratio_dbscan,
        "kmeans_hotspot_ratio": hotspot_ratio_kmeans,
        "feature_columns": feature_columns,
    }


def main() -> None:
    root_dir = Path(__file__).resolve().parents[4]
    cdc_path = root_dir / "disease_hotspot_detection" / "data" / "cdc_measles_massive.csv"
    fhir_primary = root_dir / "disease_hotspot_detection" / "data" / "ready_for_model_spatial.csv"
    fhir_fallback = root_dir / "backend" / "services" / "ml-hotspots" / "ready_for_spatial_analysis.csv"

    if not cdc_path.exists():
        raise FileNotFoundError(f"CDC dataset not found at {cdc_path}")

    cdc_df = pd.read_csv(cdc_path)
    metrics = {"cdc": summarize_cdc_metrics(cdc_df)}

    if fhir_primary.exists():
        fhir_df = pd.read_csv(fhir_primary)
        metrics["fhir"] = summarize_fhir_metrics(fhir_df)
        metrics["fhir"]["source"] = str(fhir_primary)
    elif fhir_fallback.exists():
        fhir_df = pd.read_csv(fhir_fallback)
        metrics["fhir"] = summarize_fhir_metrics(fhir_df)
        metrics["fhir"]["source"] = str(fhir_fallback)
    else:
        metrics["fhir"] = {"available": False, "reason": "file_not_found"}

    print(json.dumps(metrics, allow_nan=False))


if __name__ == "__main__":
    main()
