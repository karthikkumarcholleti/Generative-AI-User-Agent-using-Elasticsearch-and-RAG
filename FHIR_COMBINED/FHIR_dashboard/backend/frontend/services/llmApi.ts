import axios from 'axios';

// Use Next.js API proxy to avoid CORS issues
const BASE_URL = '/api/llm';

export interface PatientLite {
  id: number;
  patientId: string;
  displayName: string;
  dob?: string | null;
  gender?: string | null;
}

export interface AllSummariesResponse {
  patientId: string;
  model: string;
  summaries: Record<string, string>;
  contextCounts: {
    conditions: number;
    observations: number;
    notes: number;
  };
  generatedAt: string;
}

export interface FollowUpOption {
  text: string;
  type: string;
  action: string;
}

export interface SourceInfo {
  id?: string;  // Unique source ID for clickable functionality
  type: string;
  description: string;
}

export interface SourceDetail {
  source_id: string;
  data_type: string;
  display: string;
  value: string;
  unit: string;
  date: string;
  code: string;
  score: number;
  timestamp: string;
  filename: string;
  source_type: string;
  content: string;
  description: string;
  metadata: Record<string, unknown>;
}

export interface ChatResponse {
  response: string;
  follow_up_options?: FollowUpOption[];
  intent?: Record<string, unknown>;
  data_found?: boolean;
  retrieved_count?: number;
  session_id?: string | null;
  sources?: SourceInfo[];
  chart?: ChartPayload;  // Auto-generated chart
}

export interface VisualizationResponse {
  success: boolean;
  chart_data?: ChartPayload;
  chart_type?: string;
  patient_id: string;
  error?: string | null;
}

export interface ChartPayload {
  type: string;
  data: {
    labels: string[];
    datasets: Array<{
      label: string;
      data: Array<number | null>;
      borderColor?: string;
      backgroundColor?: string;
      borderWidth?: number;
      tension?: number;
    }>;
  };
  options: Record<string, unknown>;
  summary?: string;
}

export interface RagStatus {
  elasticsearch_connected: boolean;
  elasticsearch_url?: string | null;
  services: Record<string, string>;
}

export interface IndexAllResponse {
  success: boolean;
  message?: string;
  total_patients?: number;
  indexed_count?: number;
  errors?: string[];
  error?: string;
}

export interface GeneralHelpResponse {
  response: string;
}

const client = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 900000, // 15 minutes timeout for LLM operations (summary generation can take 10+ minutes, chat queries ~1 minute)
});

export async function getPatients(query = ''): Promise<PatientLite[]> {
  const params: Record<string, string> = {};
  if (query) {
    params.query = query;
  }
  const { data } = await client.get<PatientLite[]>('/patients', { params });
  return data;
}

export async function getAllSummaries(patientId: string): Promise<AllSummariesResponse> {
  const { data } = await client.get<AllSummariesResponse>(`/patients/${patientId}/all_summaries`);
  return data;
}

export interface LlmSummaryResponse {
  patientId: string;
  model: string;
  summary: string;
  contextCounts: {
    conditions: number;
    observations: number;
    notes: number;
  };
}

export async function getLlmSummary(patientId: string, category: string): Promise<LlmSummaryResponse> {
  const { data } = await client.get<LlmSummaryResponse>(`/patients/${patientId}/llm_summary`, {
    params: { category }
  });
  return data;
}

export async function getPatientDemographics(patientId: string) {
  const { data } = await client.get(`/patients/${patientId}/demographics`);
  return data;
}

export async function postChatQuery(patientId: string, query: string, sessionId?: string | null): Promise<ChatResponse> {
  const payload: Record<string, unknown> = {
    patient_id: patientId,
    query,
  };
  if (sessionId) {
    payload.session_id = sessionId;
  }
  const { data } = await client.post<ChatResponse>('/chat-agent/query', payload);
  return data;
}

export async function postVisualization(patientId: string, chartType: string, parameters?: Record<string, unknown>): Promise<VisualizationResponse> {
  const payload: Record<string, unknown> = {
    patient_id: patientId,
    chart_type: chartType,
  };
  if (parameters) {
    payload.parameters = parameters;
  }
  const { data } = await client.post<VisualizationResponse>('/chat-agent/visualize', payload);
  return data;
}

export async function postGroupedVisualization(patientId: string) {
  const { data } = await client.post(`/chat-agent/visualize/grouped`, null, {
    params: { patient_id: patientId },
  });
  return data;
}

export async function postIndexAllPatients(): Promise<IndexAllResponse> {
  const { data } = await client.post<IndexAllResponse>('/chat-agent/index-all-patients');
  return data;
}

export async function postIndexPatient(patientId: string) {
  const { data } = await client.post(`/chat-agent/patient/${patientId}/index`);
  return data;
}

export async function deleteConversation(patientId: string) {
  const { data } = await client.delete(`/chat-agent/patient/${patientId}/conversation`);
  return data;
}

export async function getConversation(patientId: string) {
  const { data } = await client.get(`/chat-agent/patient/${patientId}/conversation`);
  return data;
}

export async function getChatAgentStatus(): Promise<RagStatus> {
  const { data } = await client.get<RagStatus>('/chat-agent/status');
  return data;
}

export async function postGeneralMedicalHelp(question: string): Promise<GeneralHelpResponse> {
  const { data } = await client.post<GeneralHelpResponse>('/general-medical-help', { question });
  return data;
}

export async function exportPatientReport(patientId: string, format: 'html' | 'json' = 'html') {
  const { data } = await client.post('/chat-agent/export', {
    patient_id: patientId,
    export_type: format,
    include_charts: true,
    include_conversation: true,
  });
  return data;
}

export async function getSourceDetail(sourceId: string): Promise<SourceDetail> {
  const { data } = await client.get<SourceDetail>(`/chat-agent/source/${sourceId}`);
  return data;
}

export interface ChatMessagesResponse {
  patient_id: string;
  messages: Array<{
    id: string;
    sender: 'agent' | 'user';
    text?: string;
    isLoading?: boolean;
    chart?: ChartPayload | { type: 'categorized_observations'; charts: any[]; single_value_observations: any[] };
    sources?: SourceInfo[];
    createdAt: string;
  }>;
}

export async function getChatMessages(patientId: string): Promise<ChatMessagesResponse> {
  const { data } = await client.get<ChatMessagesResponse>(`/chat-agent/patient/${patientId}/messages`);
  return data;
}

export async function saveChatMessages(patientId: string, messages: ChatMessagesResponse['messages']): Promise<ChatMessagesResponse> {
  const { data } = await client.post<ChatMessagesResponse>(`/chat-agent/patient/${patientId}/messages`, {
    messages
  });
  return data;
}

export async function clearChatMessages(patientId: string) {
  const { data } = await client.delete(`/chat-agent/patient/${patientId}/messages`);
  return data;
}
