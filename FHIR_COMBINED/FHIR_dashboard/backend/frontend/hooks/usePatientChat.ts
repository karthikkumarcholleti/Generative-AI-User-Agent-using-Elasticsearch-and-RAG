import { useState, useCallback, useRef, useEffect } from 'react';
import {
  postChatQuery,
  postVisualization,
  getChatMessages,
  saveChatMessages,
  deleteConversation,
  getSourceDetail,
  type PatientLite,
  type ChartPayload,
  type FollowUpOption,
  type SourceInfo,
  type SourceDetail,
} from '@/services/llmApi';

export type ChatMessage = {
  id: string;
  sender: 'agent' | 'user';
  text?: string;
  isLoading?: boolean;
  chart?: ChartPayload | { type: 'categorized_observations'; charts: any[]; single_value_observations: any[] };
  sources?: SourceInfo[];
  createdAt: string;
};

const createId = () => `${Date.now()}-${Math.random().toString(16).slice(2)}`;

function initialMessage(patientName?: string): ChatMessage {
  return {
    id: createId(),
    sender: 'agent',
    text: patientName
      ? `I am ready to help you interpret ${patientName}'s data. Ask about observations, abnormal values, or trends to begin.`
      : 'Hello! I am your clinical data assistant. Select a patient to begin.',
    createdAt: new Date().toISOString(),
  };
}

export function usePatientChat(patient: PatientLite | null) {
  const [messages, setMessages] = useState<ChatMessage[]>([initialMessage()]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chatInput, setChatInput] = useState('');
  const [followUpOptions, setFollowUpOptions] = useState<FollowUpOption[]>([]);
  const [selectedSource, setSelectedSource] = useState<SourceDetail | null>(null);
  const [sourceModalOpen, setSourceModalOpen] = useState(false);
  const [loadingSource, setLoadingSource] = useState(false);

  const isMountedRef = useRef(true);
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    isMountedRef.current = true;
    return () => { isMountedRef.current = false; };
  }, []);

  // Reset and load messages when patient changes
  useEffect(() => {
    if (!patient) {
      setMessages([initialMessage()]);
      setFollowUpOptions([]);
      setError(null);
      return;
    }

    getChatMessages(patient.patientId)
      .then(response => {
        if (!isMountedRef.current) return;
        if (response.messages && response.messages.length > 0) {
          setMessages(response.messages as ChatMessage[]);
        } else {
          setMessages([initialMessage(patient.displayName)]);
        }
      })
      .catch(() => {
        if (isMountedRef.current) setMessages([initialMessage(patient.displayName)]);
      });
  }, [patient?.patientId]);

  // Debounced save to backend cache
  useEffect(() => {
    if (!patient || messages.length === 0) return;
    if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current);
    saveTimeoutRef.current = setTimeout(() => {
      saveChatMessages(patient.patientId, messages).catch(() => {});
    }, 500);
    return () => { if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current); };
  }, [messages, patient?.patientId]);

  const send = useCallback(async (text: string) => {
    if (!patient || !text.trim()) return;
    setError(null);
    setChatInput('');

    const userMsg: ChatMessage = {
      id: createId(), sender: 'user', text, createdAt: new Date().toISOString(),
    };
    const loadingMsg: ChatMessage = {
      id: createId(), sender: 'agent', text: 'Analyzing your question... hold on.',
      isLoading: true, createdAt: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMsg, loadingMsg]);
    setLoading(true);

    try {
      const response = await postChatQuery(patient.patientId, text);
      if (!isMountedRef.current) return;
      setMessages(prev => prev.map(m =>
        m.id === loadingMsg.id
          ? {
              ...m,
              text: response.response || 'Response received but empty.',
              isLoading: false,
              sources: response.sources ?? [],
              chart: response.chart,
            }
          : m
      ));
      setFollowUpOptions(response.follow_up_options ?? []);
    } catch (err: any) {
      if (!isMountedRef.current) return;
      const msg = err?.response?.data?.detail || err?.message || 'An error occurred.';
      setMessages(prev => prev.map(m =>
        m.id === loadingMsg.id
          ? { ...m, text: `I encountered an error: ${msg}. Please try again.`, isLoading: false }
          : m
      ));
      setError(msg);
    } finally {
      if (isMountedRef.current) setLoading(false);
    }
  }, [patient]);

  const sendVisualization = useCallback(async (option: FollowUpOption) => {
    if (!patient) return;

    const chartType = (() => {
      switch (option.action) {
        case 'create_glucose_chart': return 'glucose_trend';
        case 'create_bp_chart': return 'blood_pressure_trend';
        case 'create_hr_chart': return 'heart_rate_trend';
        case 'create_vitals_dashboard': return 'vitals_dashboard';
        default:
          if (option.text.toLowerCase().includes('glucose')) return 'glucose_trend';
          if (option.text.toLowerCase().includes('blood pressure')) return 'blood_pressure_trend';
          if (option.text.toLowerCase().includes('heart rate')) return 'heart_rate_trend';
          return 'all_observations';
      }
    })();

    const loadingMsg: ChatMessage = {
      id: createId(), sender: 'agent', text: 'Generating the requested visualization...',
      isLoading: true, createdAt: new Date().toISOString(),
    };
    setMessages(prev => [...prev, loadingMsg]);

    try {
      const response = await postVisualization(patient.patientId, chartType);
      setMessages(prev => prev.map(m =>
        m.id === loadingMsg.id
          ? {
              ...m,
              text: response.success
                ? response.chart_data?.summary || 'Chart generated successfully.'
                : `Unable to generate chart: ${response.error ?? 'Unknown error'}`,
              isLoading: false,
              chart: response.success ? response.chart_data : undefined,
            }
          : m
      ));
      setFollowUpOptions([]);
    } catch {
      setMessages(prev => prev.map(m =>
        m.id === loadingMsg.id
          ? { ...m, text: 'Unable to generate the visualization. Please try again.', isLoading: false }
          : m
      ));
    }
  }, [patient]);

  const handleFollowUp = useCallback((option: FollowUpOption) => {
    if (option.type === 'visualization') {
      void sendVisualization(option);
      return;
    }
    void send(option.text);
  }, [send, sendVisualization]);

  const handleSourceClick = useCallback(async (sourceId: string) => {
    if (!sourceId) return;
    setLoadingSource(true);
    setSourceModalOpen(true);
    try {
      const detail = await getSourceDetail(sourceId);
      setSelectedSource(detail);
    } catch {
      setSelectedSource(null);
    } finally {
      setLoadingSource(false);
    }
  }, []);

  const reset = useCallback(async () => {
    if (patient) {
      try { await deleteConversation(patient.patientId); } catch {}
    }
    setMessages([initialMessage(patient?.displayName)]);
    setFollowUpOptions([]);
    setError(null);
  }, [patient]);

  return {
    messages,
    loading,
    error,
    chatInput,
    setChatInput,
    send,
    followUpOptions,
    handleFollowUp,
    handleSourceClick,
    selectedSource,
    sourceModalOpen,
    setSourceModalOpen,
    loadingSource,
    reset,
  };
}
