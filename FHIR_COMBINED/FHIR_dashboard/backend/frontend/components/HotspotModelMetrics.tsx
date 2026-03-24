import React from 'react';
import { motion } from 'framer-motion';

export interface ModelMetricsSummary {
  cluster_count: number;
  hotspot_records: number;
  hotspot_ratio: number;
  silhouette: number;
  davies_bouldin: number;
  total_records: number;
  eps?: number;
  min_samples?: number;
  threshold_quantile?: number;
}

export interface FhirMetricsSummary {
  available: boolean;
  records?: number;
  dbscan_hotspot_ratio?: number;
  kmeans_hotspot_ratio?: number;
  feature_columns?: string[];
  source?: string;
  reason?: string;
}

interface Props {
  dbscan: ModelMetricsSummary | null;
  kmeans: ModelMetricsSummary | null;
  fhir?: FhirMetricsSummary;
}

const ratioToPercent = (value?: number) => {
  if (value === undefined || Number.isNaN(value)) return 'N/A';
  return `${(value * 100).toFixed(1)}%`;
};

const formatFloat = (value?: number, digits = 3) => {
  if (value === undefined || Number.isNaN(value)) return 'N/A';
  return value.toFixed(digits);
};

const infoRows = (
  metrics: ModelMetricsSummary | null,
  extra: Array<{ label: string; value: React.ReactNode }> = []
) => {
  if (!metrics) return null;
  const rows = [
    { label: 'Total Records', value: metrics.total_records.toLocaleString() },
    { label: 'Clusters', value: metrics.cluster_count.toLocaleString() },
    { label: 'Hotspot Records', value: metrics.hotspot_records.toLocaleString() },
    { label: 'Hotspot Ratio', value: ratioToPercent(metrics.hotspot_ratio) },
    { label: 'Silhouette Score', value: formatFloat(metrics.silhouette) },
    { label: 'Davies–Bouldin', value: formatFloat(metrics.davies_bouldin) },
    ...extra,
  ];

  return (
    <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
      {rows.map((row) => (
        <div key={row.label} className="flex flex-col rounded-lg border border-slate-200/70 bg-white/70 px-4 py-3 shadow-sm">
          <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{row.label}</dt>
          <dd className="text-base font-semibold text-slate-800">{row.value}</dd>
        </div>
      ))}
    </dl>
  );
};

const HotspotModelMetrics: React.FC<Props> = ({ dbscan, kmeans, fhir }) => {
  return (
    <motion.section
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="rounded-3xl border border-slate-200 bg-gradient-to-br from-white via-slate-50/60 to-slate-100/40 p-8 shadow-xl"
    >
      <div className="flex flex-col gap-3 mb-8">
        <h2 className="text-2xl font-bold text-slate-800">Hotspot Model Metrics</h2>
        <p className="text-sm text-slate-600 max-w-3xl">
          These metrics compare the original DBSCAN clustering with the new KMeans-based hotspot detection.
          Use them to validate that both approaches identify dense disease activity without relying on map visuals.
        </p>
      </div>

      <div className="grid gap-8 lg:grid-cols-2">
        <div className="rounded-2xl border border-sidebar-accent/40 bg-white/70 p-6 shadow-md">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-sidebar-accent">DBSCAN Baseline</h3>
              {dbscan?.eps !== undefined && (
                <p className="text-xs text-slate-500">
                  Parameters: eps={dbscan.eps}, min_samples={dbscan.min_samples}
                </p>
              )}
            </div>
          </div>
          {infoRows(dbscan)}
        </div>

        <div className="rounded-2xl border border-emerald-400/40 bg-white/70 p-6 shadow-md">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-emerald-600">KMeans Alternative</h3>
              {kmeans?.threshold_quantile !== undefined && (
                <p className="text-xs text-slate-500">
                  Hotspot Threshold: top {(kmeans.threshold_quantile * 100).toFixed(0)}% clusters by intensity
                </p>
              )}
            </div>
          </div>
          {infoRows(kmeans)}
        </div>
      </div>

      {fhir && (
        <div className="mt-10 rounded-2xl border border-slate-200 bg-white/60 p-6 shadow-md">
          <h3 className="text-lg font-semibold text-slate-800 mb-4">FHIR Dataset Coverage</h3>
          {fhir.available ? (
            <div className="grid gap-4 sm:grid-cols-3 text-sm">
              <div className="rounded-lg border border-slate-200 px-4 py-3 bg-white/70 shadow-sm">
                <p className="text-xs text-slate-500 uppercase tracking-wide">Records Evaluated</p>
                <p className="text-lg font-semibold text-slate-800">{fhir.records?.toLocaleString() ?? 'N/A'}</p>
              </div>
              <div className="rounded-lg border border-slate-200 px-4 py-3 bg-white/70 shadow-sm">
                <p className="text-xs text-slate-500 uppercase tracking-wide">DBSCAN Hotspot Ratio</p>
                <p className="text-lg font-semibold text-slate-800">{ratioToPercent(fhir.dbscan_hotspot_ratio)}</p>
              </div>
              <div className="rounded-lg border border-slate-200 px-4 py-3 bg-white/70 shadow-sm">
                <p className="text-xs text-slate-500 uppercase tracking-wide">KMeans Hotspot Ratio</p>
                <p className="text-lg font-semibold text-slate-800">{ratioToPercent(fhir.kmeans_hotspot_ratio)}</p>
              </div>
              {fhir.feature_columns && (
                <div className="sm:col-span-3 rounded-lg border border-slate-200 px-4 py-3 bg-white/70 shadow-sm">
                  <p className="text-xs text-slate-500 uppercase tracking-wide">Feature Columns</p>
                  <p className="text-sm font-medium text-slate-700">{fhir.feature_columns.join(', ')}</p>
                  {fhir.source && (
                    <p className="mt-1 text-xs text-slate-400">Source: {fhir.source}</p>
                  )}
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-slate-600">
              FHIR evaluation not available ({fhir.reason ?? 'unsupported dataset'}).
            </p>
          )}
        </div>
      )}
    </motion.section>
  );
};

export default HotspotModelMetrics;
