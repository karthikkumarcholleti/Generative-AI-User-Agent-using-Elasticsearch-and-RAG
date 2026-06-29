import { useState, useEffect } from 'react';
import { getPatients, type PatientLite } from '@/services/llmApi';

export function usePatients() {
  const [patients, setPatients] = useState<PatientLite[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getPatients('')
      .then(data => { setPatients(data); setError(null); })
      .catch(() => setError('Unable to load patients. Please try again.'))
      .finally(() => setLoading(false));
  }, []);

  return { patients, loading, error };
}
