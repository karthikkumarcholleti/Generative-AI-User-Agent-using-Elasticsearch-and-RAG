import axios from 'axios';

const client = axios.create({
  baseURL: '/api/llm',
  headers: { 'Content-Type': 'application/json' },
  timeout: 900000,
});

export interface PopulationQueryResponse {
  response: string;
  sql_used?: string | null;
  patient_count: number;
  elapsed_ms: number;
  pipeline_mode: string;
  sources: Array<{ type: string; description: string }>;
}

export async function postPopulationQuery(
  patientIds: string[],
  query: string
): Promise<PopulationQueryResponse> {
  const { data } = await client.post<PopulationQueryResponse>(
    '/chat-agent/population-query',
    { patient_ids: patientIds, query }
  );
  return data;
}
