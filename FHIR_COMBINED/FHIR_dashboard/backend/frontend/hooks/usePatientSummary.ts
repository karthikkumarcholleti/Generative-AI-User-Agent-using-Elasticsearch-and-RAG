import { useState, useCallback, useEffect } from 'react';
import { getAllSummaries } from '@/services/llmApi';

export type SummaryCategory =
  | 'patient_summary'
  | 'demographics'
  | 'conditions'
  | 'observations'
  | 'notes'
  | 'care_plans'
  | 'generative_ai';

export interface SummaryMeta {
  model?: string;
  generatedAt?: string;
}

export function usePatientSummary(patientId: string | null) {
  const [summaries, setSummaries] = useState<Partial<Record<SummaryCategory, string>>>({});
  const [contextCounts, setContextCounts] = useState({ conditions: 0, observations: 0, notes: 0 });
  const [meta, setMeta] = useState<SummaryMeta>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async (id?: string) => {
    const targetId = id ?? patientId;
    if (!targetId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getAllSummaries(targetId);
      setSummaries(data.summaries as Partial<Record<SummaryCategory, string>>);
      setContextCounts(data.contextCounts);
      setMeta({ model: data.model, generatedAt: data.generatedAt });
    } catch {
      setError('Unable to generate summaries. Please try again or refresh the page.');
    } finally {
      setLoading(false);
    }
  }, [patientId]);

  useEffect(() => {
    if (patientId) {
      setSummaries({});
      setContextCounts({ conditions: 0, observations: 0, notes: 0 });
      setMeta({});
      setError(null);
      refresh(patientId);
    }
  }, [patientId]);

  return { summaries, contextCounts, meta, loading, error, refresh };
}
