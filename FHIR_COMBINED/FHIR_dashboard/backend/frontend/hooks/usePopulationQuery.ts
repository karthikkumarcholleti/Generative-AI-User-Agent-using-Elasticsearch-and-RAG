import { useState, useCallback } from 'react';
import { postPopulationQuery, type PopulationQueryResponse } from '@/services/populationApi';

export function usePopulationQuery() {
  const [response, setResponse] = useState<PopulationQueryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');

  const submit = useCallback(async (patientIds: string[], q: string) => {
    if (!patientIds.length || !q.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await postPopulationQuery(patientIds, q);
      setResponse(result);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Population query failed. Please try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  const clear = useCallback(() => {
    setResponse(null);
    setError(null);
    setQuery('');
  }, []);

  return { response, loading, error, query, setQuery, submit, clear };
}
