import React, { useEffect, useMemo, useState, useCallback, useRef } from 'react';
import { useRouter } from 'next/router';
import Sidebar from '@/components/Sidebar';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Bot,
  ClipboardList,
  Loader2,
  RefreshCw,
  Search,
  Sparkles,
  Stethoscope,
  Activity,
  BookOpenCheck,
  Brain,
  AlertCircle,
  ShieldCheck,
  MessageCircleHeart,
  ArrowRight,
  Wand2,
  X,
  Clock,
  Minimize2,
  Maximize2,
  Users,
  ChevronRight,
} from 'lucide-react';
import {
  getPatients,
  getAllSummaries,
  getLlmSummary,
  postChatQuery,
  postVisualization,
  postGeneralMedicalHelp,
  exportPatientReport,
  deleteConversation,
  getSourceDetail,
  getChatMessages,
  saveChatMessages,
  clearChatMessages,
  type PatientLite,
  type FollowUpOption,
  type ChartPayload,
  type SourceInfo,
  type SourceDetail,
} from '@/services/llmApi';
import RechartsVisualization from '@/components/RechartsVisualization';
import SourceDetailModal from '@/components/SourceDetailModal';
import DashboardCard from '@/components/DashboardCard';
import DashboardCharts from '@/components/DashboardCharts';
import HospitalMap from '@/components/HospitalMap';
import MapProvider from '@/components/MapProvider';

type SummaryCategory =
  | 'patient_summary'
  | 'demographics'
  | 'conditions'
  | 'observations'
  | 'notes'
  | 'care_plans'
  | 'generative_ai';

type ChatMessage = {
  id: string;
  sender: 'agent' | 'user';
  text?: string;
  isLoading?: boolean;
  chart?: ChartPayload | { type: 'categorized_observations'; charts: any[]; single_value_observations: any[] };
  sources?: SourceInfo[];
  createdAt: string;
};

interface SummaryMeta {
  model?: string;
  generatedAt?: string;
}

// Helper functions for category and priority colors
const getCategoryColor = (category: string): string => {
  const colors: Record<string, string> = {
    "Cardiovascular": "bg-red-50 border-red-200 text-red-800",
    "Respiratory": "bg-blue-50 border-blue-200 text-blue-800",
    "Mental Health": "bg-purple-50 border-purple-200 text-purple-800",
    "Neurological": "bg-indigo-50 border-indigo-200 text-indigo-800",
    "Musculoskeletal": "bg-orange-50 border-orange-200 text-orange-800",
    "Gastrointestinal": "bg-green-50 border-green-200 text-green-800",
    "Renal": "bg-cyan-50 border-cyan-200 text-cyan-800",
    "Endocrine": "bg-pink-50 border-pink-200 text-pink-800",
    "Metabolic": "bg-yellow-50 border-yellow-200 text-yellow-800",
    "Oncology": "bg-rose-50 border-rose-200 text-rose-800",
    "Acute": "bg-yellow-50 border-yellow-200 text-yellow-800",
    "Other": "bg-gray-50 border-gray-200 text-gray-800"
  };
  return colors[category] || "bg-gray-50 border-gray-200 text-gray-800";
};

const getPriorityColor = (priority: string): string => {
  const colors: Record<string, string> = {
    "high": "bg-red-100 text-red-800 border-red-200",
    "medium": "bg-yellow-100 text-yellow-800 border-yellow-200",
    "low": "bg-green-100 text-green-800 border-green-200"
  };
  return colors[priority.toLowerCase()] || "bg-gray-100 text-gray-800 border-gray-200";
};

// Format LLM response for better readability
const formatLLMResponse = (text: string): React.ReactNode => {
  if (!text) return text;
  
  // Split by lines
  const lines = text.split('\n');
  const formatted: React.ReactNode[] = [];
  
  lines.forEach((line, index) => {
    const trimmed = line.trim();
    
    // Skip empty lines
    if (!trimmed) {
      formatted.push(<br key={`br-${index}`} />);
      return;
    }
    
    // Detect category headers (CARDIOVASCULAR:, METABOLIC:, etc.)
    const categoryMatch = trimmed.match(/^([A-Z\s]+):\s*$/);
    if (categoryMatch) {
      const category = categoryMatch[1].trim();
      formatted.push(
        <div key={`category-${index}`} className="mt-4 mb-2">
          <span className={`inline-block px-3 py-1 rounded-lg text-sm font-semibold border ${getCategoryColor(category)}`}>
            {category}
          </span>
        </div>
      );
      return;
    }
    
    // Detect priority markers (🔴 HIGH, 🟡 MEDIUM, 🟢 LOW)
    const priorityMatch = trimmed.match(/^([🔴🟡🟢])\s*(HIGH|MEDIUM|LOW):\s*(.+)$/);
    if (priorityMatch) {
      const [, emoji, priority, content] = priorityMatch;
      formatted.push(
        <div key={`line-${index}`} className="flex items-start gap-2 py-1 pl-4">
          <span className={`px-2 py-0.5 rounded text-xs font-semibold border ${getPriorityColor(priority)}`}>
            {priority}
          </span>
          <span className="text-slate-700 flex-1">{content}</span>
        </div>
      );
      return;
    }
    
    // Detect numbered lists (1. 2. 3. etc.)
    const numberedMatch = trimmed.match(/^(\d+)\.\s+(.+)$/);
    if (numberedMatch) {
      const [, num, content] = numberedMatch;
      
      // Check for abnormal values (high, low, elevated, abnormal, concerning)
      const isAbnormal = /(high|low|elevated|abnormal|concerning|diabetic|prediabetic|critical)/i.test(content);
      
      formatted.push(
        <div key={`line-${index}`} className="flex gap-3 py-1">
          <span className="text-sidebar-accent font-semibold flex-shrink-0">{num}.</span>
          <span className={isAbnormal ? 'text-rose-600 font-medium' : 'text-slate-700'}>
            {content}
          </span>
        </div>
      );
      return;
    }
    
    // Detect bullet points (- or •)
    if (trimmed.startsWith('- ') || trimmed.startsWith('• ')) {
      const content = trimmed.substring(2);
      const isAbnormal = /(high|low|elevated|abnormal|concerning|diabetic|prediabetic|critical)/i.test(content);
      
      formatted.push(
        <div key={`line-${index}`} className="flex gap-3 py-1">
          <span className="text-sidebar-accent flex-shrink-0">•</span>
          <span className={isAbnormal ? 'text-rose-600 font-medium' : 'text-slate-700'}>
            {content}
          </span>
        </div>
      );
      return;
    }
    
    // Regular paragraph text
    const isAbnormal = /(abnormal|concerning|high|low|elevated|critical|diabetic|prediabetic)/i.test(trimmed);
    formatted.push(
      <p key={`line-${index}`} className={isAbnormal ? 'text-rose-600 font-medium py-1' : 'text-slate-700 py-1'}>
        {trimmed}
      </p>
    );
  });
  
  return <div className="space-y-1">{formatted}</div>;
};

const SUMMARY_CATEGORIES: Array<{
  id: SummaryCategory;
  label: string;
  description: string;
  icon: React.ComponentType<{ size?: number }>;
}> = [
  {
    id: 'patient_summary',
    label: 'Patient Summary',
    description: 'LLM-generated overview for clinical review',
    icon: Sparkles,
  },
  {
    id: 'demographics',
    label: 'Demographics',
    description: 'Patient background and identifiers',
    icon: ClipboardList,
  },
  {
    id: 'conditions',
    label: 'Conditions',
    description: 'Diagnoses, statuses, and timelines',
    icon: Stethoscope,
  },
  {
    id: 'observations',
    label: 'Observations',
    description: 'Vital signs, labs, and notable values',
    icon: Activity,
  },
  {
    id: 'notes',
    label: 'Clinical Notes',
    description: 'Provider documentation and key excerpts',
    icon: BookOpenCheck,
  },
  {
    id: 'care_plans',
    label: 'Care Plans',
    description: 'AI-generated recommendations & planning',
    icon: Brain,
  },
  {
    id: 'generative_ai',
    label: 'Generative AI Chat',
    description: 'Question the RAG-powered clinical assistant',
    icon: Bot,
  },
];

// Section navigation items for left sidebar
const SECTION_NAV_ITEMS: Array<{
  id: SectionType;
  label: string;
  icon: React.ComponentType<{ size?: number }>;
}> = [
  { id: 'patients', label: 'Patients', icon: Users },
  { id: 'demographics', label: 'Demographics', icon: ClipboardList },
  { id: 'observations', label: 'Observations', icon: Activity },
  { id: 'conditions', label: 'Conditions', icon: Stethoscope },
  { id: 'notes', label: 'Notes', icon: BookOpenCheck },
  { id: 'care_plans', label: 'Care Plans', icon: Brain },
  { id: 'chat', label: 'AI Chat Interface', icon: Bot },
];

const QUICK_QUESTIONS = [
  'Show the abnormal values for this patient',
  'Summarize recent vital sign trends',
  'What are the latest lab results?',
  'Generate a blood pressure trend chart',
  'Create a glucose trend visualization',
  'Provide diabetes-related insights',
];

const createMessageId = () => `${Date.now()}-${Math.random().toString(16).slice(2)}`;

function formatSummary(text: string): string {
  const escapeHtml = (value: string) =>
    value
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

  const escaped = escapeHtml(text);
  const bolded = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  const italicized = bolded.replace(/\*(.*?)\*/g, '<em>$1</em>');
  const headings = italicized
    .replace(/^## (.*)$/gm, '<h4 class="text-lg font-semibold mt-4 mb-2 text-slate-800">$1</h4>')
    .replace(/^# (.*)$/gm, '<h3 class="text-xl font-semibold mt-4 mb-3 text-slate-900">$1</h3>');
  return headings.replace(/\n/g, '<br />');
}

function SummarySkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 3 }).map((_, idx) => (
        <motion.div
          key={idx}
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: idx * 0.1, duration: 0.3 }}
          className="h-16 bg-gradient-to-r from-slate-100 via-slate-50 to-slate-100 rounded-xl border border-slate-200 animate-pulse"
        />
      ))}
    </div>
  );
}

function SummaryCardSkeleton() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-4"
    >
      <div className="h-6 bg-slate-200 rounded w-3/4 animate-pulse" />
      <div className="space-y-2">
        <div className="h-4 bg-slate-100 rounded w-full animate-pulse" />
        <div className="h-4 bg-slate-100 rounded w-5/6 animate-pulse" />
        <div className="h-4 bg-slate-100 rounded w-4/6 animate-pulse" />
        <div className="h-4 bg-slate-100 rounded w-5/6 animate-pulse" />
      </div>
    </motion.div>
  );
}

// Section type for navigation
type SectionType = 'patients' | 'demographics' | 'observations' | 'conditions' | 'notes' | 'care_plans' | 'chat';

export default function GenerativeAIPage() {
  const router = useRouter();
  
  // Patient and data state
  const [patients, setPatients] = useState<PatientLite[]>([]);
  const [patientsLoading, setPatientsLoading] = useState(true);
  const [patientsError, setPatientsError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedPatient, setSelectedPatient] = useState<PatientLite | null>(null);

  // Summary state
  const [summaries, setSummaries] = useState<Partial<Record<SummaryCategory, string>>>({});
  const [contextCounts, setContextCounts] = useState({ conditions: 0, observations: 0, notes: 0 });
  const [summaryMeta, setSummaryMeta] = useState<SummaryMeta>({});
  const [isGeneratingSummaries, setIsGeneratingSummaries] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [displayedSummary, setDisplayedSummary] = useState('');

  // Section navigation state (NEW)
  const [activeSection, setActiveSection] = useState<SectionType>('patients');
  const [sectionHistory, setSectionHistory] = useState<Map<string, SectionType>>(new Map()); // patientId -> lastSection
  const [isGenerativeAIMinimized, setIsGenerativeAIMinimized] = useState(false);
  const [isChatMinimized, setIsChatMinimized] = useState(false);
  const [unreadMessages, setUnreadMessages] = useState(0);

  // Chat state
  const [messages, setMessages] = useState<ChatMessage[]>(() => [
    {
      id: createMessageId(),
      sender: 'agent',
      text: 'Hello! I am your clinical data assistant. Select a patient to begin and ask any question about their observations, conditions, or overall progress.',
      createdAt: new Date().toISOString(),
    },
  ]);
  const [followUpOptions, setFollowUpOptions] = useState<FollowUpOption[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [chatInput, setChatInput] = useState('');


  const [generalQuestion, setGeneralQuestion] = useState('');
  const [generalAnswer, setGeneralAnswer] = useState<string | null>(null);
  const [generalLoading, setGeneralLoading] = useState(false);
  const [generalError, setGeneralError] = useState<string | null>(null);

  // Source detail modal state
  const [selectedSource, setSelectedSource] = useState<SourceDetail | null>(null);
  const [sourceModalOpen, setSourceModalOpen] = useState(false);
  const [loadingSourceDetail, setLoadingSourceDetail] = useState(false);

  // Track component mount status to handle responses that arrive after tab switch
  const isMountedRef = useRef(true);

  // Load patients on mount
  useEffect(() => {
    async function loadPatients() {
      try {
        setPatientsLoading(true);
        const data = await getPatients('');
        setPatients(data);
        setPatientsError(null);
      } catch (error) {
        setPatientsError('Unable to load patients. Please try again or contact support if the issue persists.');
      } finally {
        setPatientsLoading(false);
      }
    }

    loadPatients();
  }, []);

  // Note: Restore state useEffect moved after generateSummaries definition to avoid hoisting issue

  // Save state to URL and localStorage when patient or section changes
  useEffect(() => {
    if (selectedPatient) {
      // Update URL params
      const currentPatientId = router.query.patientId as string;
      if (currentPatientId !== selectedPatient.patientId) {
        router.replace({
          pathname: router.pathname,
          query: { ...router.query, patientId: selectedPatient.patientId }
        }, undefined, { shallow: true });
      }

      // Save UI state to localStorage (NO messages - messages are in backend cache)
      const stateToSave = {
        patientId: selectedPatient.patientId,
        activeSection,
        isChatMinimized,
      };
      localStorage.setItem('generativeAIState', JSON.stringify(stateToSave));
    }
  }, [selectedPatient, activeSection, isChatMinimized, router]);

  // Save messages to backend cache whenever they change (with debouncing)
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  useEffect(() => {
    if (selectedPatient && messages.length > 0) {
      // Clear previous timeout to debounce saves
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
      
      // Debounce save by 500ms to prevent race conditions and reduce backend load
      saveTimeoutRef.current = setTimeout(() => {
        saveChatMessages(selectedPatient.patientId, messages)
          .catch(err => {
            console.error('Failed to save messages to backend:', err);
            // TODO: Could show user-friendly error notification here
          });
      }, 500);
      
      return () => {
        if (saveTimeoutRef.current) {
          clearTimeout(saveTimeoutRef.current);
        }
      };
    }
  }, [messages, selectedPatient]);

  // Auto-minimize when navigating away from Generative-AI page
  useEffect(() => {
    // Check current route and auto-minimize if not on generative-ai
    if (router.pathname !== '/generative-ai') {
      setIsGenerativeAIMinimized(true);
      // Save minimized state (NO messages - messages are in backend cache)
      if (selectedPatient) {
        const stateToSave = {
          patientId: selectedPatient.patientId,
          activeSection,
          isChatMinimized,
          isMinimized: true,
        };
        localStorage.setItem('generativeAIState', JSON.stringify(stateToSave));
      }
    } else {
      // If on generative-ai page, check if we should restore
      // If coming from another page, restore state (don't force minimize)
      const savedState = localStorage.getItem('generativeAIState');
      if (savedState) {
        try {
          const parsed = JSON.parse(savedState);
          // Only restore minimized state if explicitly set, otherwise show page
          if (parsed.isMinimized === false) {
            setIsGenerativeAIMinimized(false);
          } else if (parsed.isMinimized === true) {
            // Keep minimized if explicitly minimized
            setIsGenerativeAIMinimized(true);
          } else {
            // Default: show page when navigating to it
            setIsGenerativeAIMinimized(false);
          }
        } catch (e) {
          // Default: show page
          setIsGenerativeAIMinimized(false);
        }
      } else {
        // No saved state, show page
        setIsGenerativeAIMinimized(false);
      }
    }

    const handleRouteChange = (url: string) => {
      // If navigating away from generative-ai page, minimize it and save state
      if (!url.includes('/generative-ai')) {
        setIsGenerativeAIMinimized(true);
        // Save minimized state (NO messages - messages are in backend cache)
        if (selectedPatient) {
          const stateToSave = {
            patientId: selectedPatient.patientId,
            activeSection,
            isChatMinimized,
            isMinimized: true,
          };
          localStorage.setItem('generativeAIState', JSON.stringify(stateToSave));
        }
      } else {
        // If navigating to generative-ai page, restore state (clear minimized)
        const savedState = localStorage.getItem('generativeAIState');
        if (savedState) {
          try {
            const parsed = JSON.parse(savedState);
            parsed.isMinimized = false;
            localStorage.setItem('generativeAIState', JSON.stringify(parsed));
          } catch (e) {
            // Ignore errors
          }
        }
        setIsGenerativeAIMinimized(false);
      }
    };

    router.events?.on('routeChangeStart', handleRouteChange);
    return () => {
      router.events?.off('routeChangeStart', handleRouteChange);
    };
  }, [router.pathname, router, selectedPatient, activeSection, isChatMinimized, messages]);

  // Track component mount status
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  // Fetch messages from backend when switching to chat section
  useEffect(() => {
    if (activeSection === 'chat' && selectedPatient) {
      let pollInterval: NodeJS.Timeout | null = null;
      let pollCount = 0;
      const maxPolls = 600; // ~15 minutes max (600 * 1.5s = 900s) - LLM queries can take up to 15 minutes for complex queries
      
      // Fetch messages from backend cache (like summaries)
      getChatMessages(selectedPatient.patientId)
        .then(response => {
          if (response.messages && response.messages.length > 0) {
            // Check if current messages are just the initial state
            setMessages(prev => {
              const isInitialState = prev.length === 1 && 
                prev[0].sender === 'agent' && 
                (prev[0].text?.includes('ready to help') || prev[0].text?.includes('Hello!'));
              
              // Only restore if we have initial state or no messages
              // This prevents overwriting messages that were just sent
              if (isInitialState || prev.length === 0) {
                // Check for loading messages and set loading state
                const hasLoadingMessages = response.messages.some((msg: ChatMessage) => msg.isLoading === true);
                if (hasLoadingMessages) {
                  setChatLoading(true);
                  
                  // Poll backend to check if response arrived
                  pollInterval = setInterval(() => {
                    pollCount++;
                    
                    if (!isMountedRef.current) {
                      if (pollInterval) clearInterval(pollInterval);
                      return;
                    }
                    
                    // Stop polling after max attempts (15 minutes - matches network timeout)
                    if (pollCount > maxPolls) {
                      if (pollInterval) clearInterval(pollInterval);
                      setChatLoading(false);
                      setChatError('Response is taking longer than expected (over 15 minutes). The query may still be processing on the backend. Please wait a moment and refresh the page, or try a simpler query.');
                      return;
                    }
                    
                    getChatMessages(selectedPatient.patientId)
                      .then(updatedResponse => {
                        if (updatedResponse.messages) {
                          const stillLoading = updatedResponse.messages.some((msg: ChatMessage) => msg.isLoading === true);
                          if (!stillLoading) {
                            // Response came back! Update UI automatically
                            setMessages(updatedResponse.messages);
                            setChatLoading(false);
                            if (pollInterval) clearInterval(pollInterval);
                          }
                        }
                      })
                      .catch((err) => {
                        // On error, stop polling but don't show error (might be temporary)
                        if (pollInterval) clearInterval(pollInterval);
                        setChatLoading(false);
                        console.error('Polling error:', err);
                      });
                  }, 1500); // Check every 1.5 seconds
                } else {
                  setChatLoading(false);
                }
                return response.messages;
              }
              return prev;
            });
          }
        })
        .catch(err => {
          console.error('Failed to fetch messages from backend:', err);
          // If fetch fails, keep current messages (don't reset)
        });
      
      // Cleanup function - properly clean up polling interval
      return () => {
        if (pollInterval) {
          clearInterval(pollInterval);
        }
      };
    }
  }, [activeSection, selectedPatient]); // Only depend on activeSection and selectedPatient

  // Update displayed summary when category changes (preserved for typing animation)
  useEffect(() => {
    if (activeSection === 'chat') {
      setDisplayedSummary('');
      return;
    }

    // Map section to category
    const sectionToCategory: Record<SectionType, SummaryCategory> = {
      'patients': 'patient_summary',
      'demographics': 'demographics',
      'observations': 'observations',
      'conditions': 'conditions',
      'notes': 'notes',
      'care_plans': 'care_plans',
      'chat': 'generative_ai'
    };

    const category = sectionToCategory[activeSection];
    const summary = category ? summaries[category] : null;
    
    if (!summary) {
      setDisplayedSummary('');
      return;
    }

    setDisplayedSummary('');
    let index = 0;
    const speed = summary.length > 4000 ? 2 : 6;
    const interval = window.setInterval(() => {
      index += speed;
      setDisplayedSummary(summary.slice(0, index));
      if (index >= summary.length) {
        window.clearInterval(interval);
      }
    }, 16);

    return () => window.clearInterval(interval);
  }, [activeSection, summaries]);

  const filteredPatients = useMemo(() => {
    if (!searchTerm.trim()) {
      return patients;
    }
    const term = searchTerm.toLowerCase();
    return patients.filter((patient) =>
      patient.patientId.toLowerCase().includes(term) ||
      patient.displayName.toLowerCase().includes(term)
    );
  }, [patients, searchTerm]);

  const resetConversation = useCallback(() => {
    setMessages([
      {
        id: createMessageId(),
        sender: 'agent',
        text: 'I am ready to help you interpret this patient\'s data. Ask about observations, abnormal values, or trends to begin.',
        createdAt: new Date().toISOString(),
      },
    ]);
    setFollowUpOptions([]);
    setChatError(null);
  }, []);

  // Section navigation handlers (NEW)
  const handleSectionChange = useCallback((section: SectionType) => {
    setActiveSection(section);
    
    // Save section history for current patient
    if (selectedPatient) {
      setSectionHistory(prev => {
        const newMap = new Map(prev);
        newMap.set(selectedPatient.patientId, section);
        return newMap;
      });
      
      // Save UI state to localStorage (NO messages - messages are in backend cache)
      const stateToSave = {
        patientId: selectedPatient.patientId,
        activeSection: section,
        isChatMinimized: section !== 'chat',
      };
      localStorage.setItem('generativeAIState', JSON.stringify(stateToSave));
    }
    
    // If switching to chat, messages will be fetched by useEffect
    if (section === 'chat') {
      setIsChatMinimized(false);
    } else {
      // If switching to another section, auto-minimize chat
      if (activeSection === 'chat') {
        setIsChatMinimized(true);
      }
    }
  }, [selectedPatient, activeSection]);

  const handleSelectPatient = useCallback(async (patient: PatientLite) => {
    // Clear messages when switching to a different patient
    const previousPatientId = selectedPatient?.patientId;
    if (previousPatientId && previousPatientId !== patient.patientId) {
      // Reset messages to initial state when switching patients
      setMessages([
        {
          id: createMessageId(),
          sender: 'agent',
          text: 'Hello! I am your clinical data assistant. Select a patient to begin and ask any question about their observations, conditions, or overall progress.',
          createdAt: new Date().toISOString(),
        },
      ]);
      setFollowUpOptions([]);
    }
    
    setSelectedPatient(patient);
    
    // Restore last section for this patient, or default to 'patients'
    const lastSection = sectionHistory.get(patient.patientId) || 'patients';
    setActiveSection(lastSection);
    
    // Map section to category for backward compatibility
    const sectionToCategory: Record<SectionType, SummaryCategory> = {
      'patients': 'patient_summary',
      'demographics': 'demographics',
      'observations': 'observations',
      'conditions': 'conditions',
      'notes': 'notes',
      'care_plans': 'care_plans',
      'chat': 'generative_ai'
    };
    // Note: activeSection is now used directly, no need for activeCategory
    
    setSummaries({});
    setContextCounts({ conditions: 0, observations: 0, notes: 0 });
    setSummaryMeta({});
    setSummaryError(null);
    resetConversation();
    setIsChatMinimized(false);

    try {
      await deleteConversation(patient.patientId);
    } catch (error) {
      // Silently handle conversation clearing errors
    }

    await generateSummaries(patient.patientId);
  }, [resetConversation, sectionHistory]);

  const generateSummaries = useCallback(async (patientId: string, retryCount = 0) => {
    try {
      setIsGeneratingSummaries(true);
      setSummaryError(null);
      const data = await getAllSummaries(patientId);
      setSummaries(data.summaries as Partial<Record<SummaryCategory, string>>);
      setContextCounts(data.contextCounts);
      setSummaryMeta({ model: data.model, generatedAt: data.generatedAt });
      // Mark summaries as generated in localStorage
      const savedState = localStorage.getItem('generativeAIState');
      if (savedState) {
        try {
          const parsed = JSON.parse(savedState);
          parsed.summariesGenerated = true;
          localStorage.setItem('generativeAIState', JSON.stringify(parsed));
        } catch (e) {
          // Ignore errors
        }
      }
      // Success - always set loading to false
      setIsGeneratingSummaries(false);
    } catch (error: any) {
      console.error('Summary generation error:', error);
      // Retry once if first attempt fails (common on first load)
      if (retryCount === 0) {
        console.log('Retrying summary generation...');
        setTimeout(() => {
          generateSummaries(patientId, 1);
        }, 2000);
      } else {
        setSummaryError('Unable to generate summaries. Please try again or refresh the page.');
      setIsGeneratingSummaries(false);
      }
    }
  }, []);

  // Restore state from URL params and localStorage on mount (moved after generateSummaries definition)
  useEffect(() => {
    // Only restore if we're on the generative-ai page
    if (router.pathname !== '/generative-ai') {
      return;
    }

    // Check URL params for patient ID
    const patientIdFromUrl = router.query.patientId as string;
    
    // Check localStorage for UI state (NO messages - messages are in backend cache)
    const savedState = localStorage.getItem('generativeAIState');
    let savedPatientId: string | null = null;
    let savedSection: SectionType = 'patients';
    let savedChatMinimized = false;
    let savedIsMinimized = false;
    
    if (savedState) {
      try {
        const parsed = JSON.parse(savedState);
        savedPatientId = parsed.patientId || null;
        savedSection = parsed.activeSection || 'patients';
        savedChatMinimized = parsed.isChatMinimized || false;
        savedIsMinimized = parsed.isMinimized || false;
      } catch (e) {
        console.error('Error parsing saved state:', e);
      }
    }

    // Priority: URL param > localStorage (only if summaries were already generated) > nothing
    // Don't auto-select on fresh page load - only restore if URL param exists or summaries were already generated
    // Check if summaries were already generated by checking if savedPatientId has summaries flag
    const hasExistingSummaries = savedState ? (() => {
      try {
        const parsed = JSON.parse(savedState);
        return parsed.summariesGenerated === true;
      } catch {
        return false;
      }
    })() : false;
    
    // Only restore patient if:
    // 1. URL param exists (user navigated with patient ID), OR
    // 2. localStorage has patient ID AND summaries were already generated (restore existing session)
    const patientIdToRestore = patientIdFromUrl || (hasExistingSummaries && savedPatientId ? savedPatientId : null);
    
    // Restore patient if needed (but don't auto-generate summaries on fresh page load)
    if (patientIdToRestore && patients.length > 0 && !selectedPatient) {
      const patient = patients.find(p => p.patientId === patientIdToRestore);
      if (patient) {
        setSelectedPatient(patient);
        setActiveSection(savedSection);
        setIsChatMinimized(savedChatMinimized);
        setIsGenerativeAIMinimized(savedIsMinimized);
        
        // Messages will be fetched from backend by useEffect when activeSection is 'chat'
        // No need to restore messages here - backend cache handles it
        
        // If restoring to chat section, ensure messages are visible
        if (savedSection === 'chat') {
          setIsChatMinimized(false);
        }
        
        // Only generate summaries if:
        // 1. URL param exists (user explicitly navigated to this patient), OR
        // 2. Summaries were already generated (restoring existing session)
        // Don't auto-generate on fresh page load without URL param
        if (!isGeneratingSummaries) {
          if (patientIdFromUrl || hasExistingSummaries) {
            generateSummaries(patientIdToRestore);
          }
          // If no URL param and no existing summaries, don't generate - wait for user to select patient
        }
      }
    } else if (selectedPatient && !savedIsMinimized && isGenerativeAIMinimized) {
      // If patient is already selected but page is minimized, and localStorage says not minimized,
      // restore the page (this happens when sidebar sets isMinimized = false)
      setIsGenerativeAIMinimized(false);
      if (savedSection) {
        setActiveSection(savedSection);
      }
      if (savedChatMinimized !== undefined) {
        setIsChatMinimized(savedChatMinimized);
      }
    }
  }, [patients, router.query.patientId, router.pathname, selectedPatient, isGeneratingSummaries, generateSummaries]);

  // Watch for localStorage changes when on generative-ai route (for sidebar restore)
  useEffect(() => {
    if (router.pathname !== '/generative-ai') {
      return;
    }

    const checkRestore = () => {
      const savedState = localStorage.getItem('generativeAIState');
      if (savedState && selectedPatient) {
        try {
          const parsed = JSON.parse(savedState);
          // If localStorage says not minimized but component is minimized, restore
          if (!parsed.isMinimized && isGenerativeAIMinimized) {
            setIsGenerativeAIMinimized(false);
            if (parsed.activeSection) {
              setActiveSection(parsed.activeSection);
            }
            if (parsed.isChatMinimized !== undefined) {
              setIsChatMinimized(parsed.isChatMinimized);
            }
          }
        } catch (e) {
          // Ignore errors
        }
      }
    };

    // Check immediately
    checkRestore();

    // Also listen for storage events (when sidebar updates localStorage)
    window.addEventListener('storage', checkRestore);
    
    // Poll localStorage every 500ms when minimized (for sidebar restore)
    let pollInterval: NodeJS.Timeout | null = null;
    if (isGenerativeAIMinimized) {
      pollInterval = setInterval(checkRestore, 500);
    }

    return () => {
      window.removeEventListener('storage', checkRestore);
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  }, [router.pathname, selectedPatient, isGenerativeAIMinimized]);

  // Generate individual summary on-demand when category is clicked
  const generateCategorySummary = useCallback(async (patientId: string, category: SummaryCategory) => {
    // Skip if it's generative_ai category or already exists
    if (category === 'generative_ai' || summaries[category]) {
      return;
    }

    try {
      setIsGeneratingSummaries(true);
      setSummaryError(null);
      const data = await getLlmSummary(patientId, category);
      
      // Update summaries with the new one
      setSummaries(prev => ({
        ...prev,
        [category]: data.summary
      }));
      
      // Update context counts if available
      if (data.contextCounts) {
        setContextCounts(prev => ({
          ...prev,
          ...data.contextCounts
        }));
      }
      
      // Update meta if not set
      if (!summaryMeta.model) {
        setSummaryMeta({ model: data.model });
      }
    } catch (error) {
      setSummaryError(`Unable to generate ${category} summary. Please try again.`);
    } finally {
      setIsGeneratingSummaries(false);
    }
  }, [summaries, summaryMeta]);

  const sendChatMessage = useCallback(async (input: string) => {
    if (!selectedPatient) {
      setChatError('Select a patient before using the assistant.');
      return;
    }
    const trimmed = input.trim();
    if (!trimmed) {
      return;
    }

    setChatError(null);
    setChatInput('');
    // Switch to chat section when sending message
    setActiveSection('chat');
    setIsChatMinimized(false);
    const userMessage: ChatMessage = {
      id: createMessageId(),
      sender: 'user',
      text: trimmed,
      createdAt: new Date().toISOString(),
    };
    const loadingMessage: ChatMessage = {
      id: createMessageId(),
      sender: 'agent',
      text: 'Analyzing your question... hold on.',
      isLoading: true,
      createdAt: new Date().toISOString(),
    };

    const updatedMessages = [...messages, userMessage, loadingMessage];
    setMessages(updatedMessages);
    setChatLoading(true);

    // Save loading state to backend cache immediately (so it persists if user switches tabs)
    // This is handled by useEffect that watches messages

    try {
      const response = await postChatQuery(selectedPatient.patientId, trimmed);
      
      // Validate response
      if (!response) {
        throw new Error('No response received from server');
      }
      
      if (!response.response) {
        console.warn('Response missing text field:', response);
        // Use a default message if response text is missing
        response.response = 'I received your query but the response format was unexpected. Please try again.';
      }
      
      // Update messages with response
      const finalMessages = updatedMessages.map((message) =>
          message.id === loadingMessage.id
            ? {
                ...message,
                text: response.response || 'Response received but empty.',
                isLoading: false,
                sources: response.sources ?? [],
                chart: response.chart,  // Include auto-generated chart
              }
            : message
      );

      // Display immediately if component is still mounted (user sees response right away)
      if (isMountedRef.current) {
        setMessages(finalMessages);
        setFollowUpOptions(response.follow_up_options ?? []);
        setChatInput('');
        setChatLoading(false);
      } else {
        // Component unmounted, but still save to backend cache
        console.log('Component unmounted, saving response to backend cache');
      }

      // Save to backend cache (handled by useEffect that watches messages)
    } catch (error: any) {
      console.error('Chat query error:', error);
      console.error('Error details:', {
        message: error?.message,
        response: error?.response?.data,
        status: error?.response?.status,
        code: error?.code
      });
      
      const errorMessage = error?.response?.data?.detail || error?.response?.data?.message || error?.message || 'An error occurred while processing your request. Please check the console for details.';
      
      const errorMessages = updatedMessages.map((message) =>
          message.id === loadingMessage.id
            ? {
                ...message,
                text: `I encountered an error: ${errorMessage}. Please try again or rephrase your question.`,
                isLoading: false,
              }
            : message
      );

      // Display error immediately if component is still mounted
      if (isMountedRef.current) {
        setMessages(errorMessages);
        setChatError(errorMessage);
      }

      // Save error state to backend cache (handled by useEffect that watches messages)
    } finally {
      if (isMountedRef.current) {
      setChatLoading(false);
    }
    }
  }, [selectedPatient, messages]);

  const handleVisualization = useCallback(async (option: FollowUpOption) => {
    if (!selectedPatient) {
      setChatError('Select a patient before creating visualizations.');
      return;
    }

    const chartType = (() => {
      switch (option.action) {
        case 'create_glucose_chart':
          return 'glucose_trend';
        case 'create_bp_chart':
          return 'blood_pressure_trend';
        case 'create_hr_chart':
          return 'heart_rate_trend';
        case 'create_vitals_dashboard':
          return 'vitals_dashboard';
        case 'create_chart':
        default:
          if (option.text.toLowerCase().includes('abnormal')) return 'abnormal_values';
          if (option.text.toLowerCase().includes('glucose')) return 'glucose_trend';
          if (option.text.toLowerCase().includes('blood pressure') || option.text.toLowerCase().includes('bp')) return 'blood_pressure_trend';
          if (option.text.toLowerCase().includes('heart rate')) return 'heart_rate_trend';
          return 'all_observations';
      }
    })();

    const loadingMessage: ChatMessage = {
      id: createMessageId(),
      sender: 'agent',
      text: 'Generating the requested visualization...',
      isLoading: true,
      createdAt: new Date().toISOString(),
    };
    const updatedMessages = [...messages, loadingMessage];
    setMessages(updatedMessages);

    // Save loading state to backend cache immediately (handled by useEffect that watches messages)

    try {
      const response = await postVisualization(selectedPatient.patientId, chartType);
      const finalMessages = updatedMessages.map((message) =>
          message.id === loadingMessage.id
            ? {
                ...message,
                text: response.success
                  ? response.chart_data?.summary
                    ? `Chart generated successfully.\n\n${response.chart_data.summary}`
                    : 'Chart generated successfully. Displaying data below.'
                  : `Unable to generate chart: ${response.error ?? 'Unknown error'}`,
                isLoading: false,
                chart: response.success ? response.chart_data : undefined,
              }
            : message
      );

      // Display immediately if component is still mounted
      if (isMountedRef.current) {
        setMessages(finalMessages);
        setFollowUpOptions([]);
      }

      // Save to backend cache (handled by useEffect that watches messages)
    } catch (error) {
      const errorMessages = updatedMessages.map((message) =>
          message.id === loadingMessage.id
            ? {
                ...message,
                text: 'Unable to generate the visualization. Please try again.',
                isLoading: false,
              }
            : message
      );

      // Display error immediately if component is still mounted
      if (isMountedRef.current) {
        setMessages(errorMessages);
      }

      // Save error state to backend cache (handled by useEffect that watches messages)
    }
  }, [selectedPatient, messages]);

  const handleSourceClick = useCallback(async (sourceId: string) => {
    if (!sourceId) return;
    
    setLoadingSourceDetail(true);
    setSourceModalOpen(true);
    
    try {
      const sourceDetail = await getSourceDetail(sourceId);
      setSelectedSource(sourceDetail);
    } catch (error) {
      console.error('Failed to load source detail:', error);
      setSelectedSource(null);
      setChatError('Failed to load source details. Please try again.');
    } finally {
      setLoadingSourceDetail(false);
    }
  }, []);

  const handleFollowUp = useCallback((option: FollowUpOption) => {
    setActiveSection('chat');
    setIsChatMinimized(false);
    if (option.type === 'visualization') {
      void handleVisualization(option);
      return;
    }
    if (option.action === 'refresh_data' && selectedPatient) {
      void generateSummaries(selectedPatient.patientId);
      return;
    }
    if (option.type === 'report' && selectedPatient) {
      (async () => {
        const loadingMessage: ChatMessage = {
          id: createMessageId(),
          sender: 'agent',
          text: 'Generating the comprehensive patient report... ',
          isLoading: true,
          createdAt: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, loadingMessage]);
        try {
          const report = await exportPatientReport(selectedPatient.patientId, 'html');
          setMessages((prev) =>
            prev.map((message) =>
              message.id === loadingMessage.id
                ? {
                    ...message,
                    text: 'The patient report is ready. You can open it in a new window.',
                    isLoading: false,
                    chart: undefined,
                  }
                : message
            )
          );
          const blob = new Blob([report.file_content ?? ''], { type: 'text/html' });
          const url = URL.createObjectURL(blob);
          window.open(url, '_blank');
        } catch (error) {
          setMessages((prev) =>
            prev.map((message) =>
              message.id === loadingMessage.id
                ? {
                    ...message,
                    text: 'Unable to generate the report. Please try again.',
                    isLoading: false,
                  }
                : message
            )
          );
        }
      })();
      return;
    }

    void sendChatMessage(option.text);
  }, [generateSummaries, handleVisualization, selectedPatient, sendChatMessage]);


  const handleAskGeneralQuestion = useCallback(async () => {
    const question = generalQuestion.trim();
    if (!question) {
      return;
    }
    setGeneralLoading(true);
    setGeneralError(null);
    try {
      const response = await postGeneralMedicalHelp(question);
      setGeneralAnswer(response.response);
      setGeneralQuestion('');
    } catch (error) {
      setGeneralError('Unable to fetch medical reference. Please try again.');
    } finally {
      setGeneralLoading(false);
    }
  }, [generalQuestion]);

  // Minimize/Close handlers (NEW)
  const handleMinimizeGenerativeAI = useCallback(() => {
    setIsGenerativeAIMinimized(true);
    // Save minimized state (NO messages - messages are in backend cache)
    if (selectedPatient) {
      const stateToSave = {
        patientId: selectedPatient.patientId,
        activeSection,
        isChatMinimized,
        isMinimized: true,
      };
      localStorage.setItem('generativeAIState', JSON.stringify(stateToSave));
    }
  }, [selectedPatient, activeSection, isChatMinimized]);

  const handleMaximizeGenerativeAI = useCallback(() => {
    setIsGenerativeAIMinimized(false);
    // Clear minimized state (messages are in backend cache, will be fetched by useEffect)
    if (selectedPatient) {
      const stateToSave = {
        patientId: selectedPatient.patientId,
        activeSection,
        isChatMinimized,
        isMinimized: false,
      };
      localStorage.setItem('generativeAIState', JSON.stringify(stateToSave));
      
      // If restoring to chat section, ensure chat is not minimized
      if (activeSection === 'chat') {
        setIsChatMinimized(false);
      }
    }
  }, [selectedPatient, activeSection, isChatMinimized]);

  const handleCloseGenerativeAI = useCallback(() => {
    router.push('/');
  }, [router]);

  const handleCloseChat = useCallback(() => {
    // Return to previous section
    if (selectedPatient) {
      const previousSection = sectionHistory.get(selectedPatient.patientId) || 'patients';
      setActiveSection(previousSection);
      
      // Map section to category
      const sectionToCategory: Record<SectionType, SummaryCategory> = {
        'patients': 'patient_summary',
        'demographics': 'demographics',
        'observations': 'observations',
        'conditions': 'conditions',
        'notes': 'notes',
        'care_plans': 'care_plans',
        'chat': 'generative_ai'
      };
      // Note: activeSection is now used directly, no need for activeCategory
    }
    setIsChatMinimized(false);
  }, [selectedPatient, sectionHistory]);

  const handleMinimizeChat = useCallback(() => {
    setIsChatMinimized(true);
    setUnreadMessages(0); // Reset unread when minimized
    // Save UI state (NO messages - messages are in backend cache)
    if (selectedPatient) {
      const stateToSave = {
        patientId: selectedPatient.patientId,
        activeSection,
        isChatMinimized: true,
        isMinimized: isGenerativeAIMinimized,
      };
      localStorage.setItem('generativeAIState', JSON.stringify(stateToSave));
    }
  }, [selectedPatient, activeSection, isGenerativeAIMinimized]);

  const handleMaximizeChat = useCallback(() => {
    setIsChatMinimized(false);
    setActiveSection('chat');
    setUnreadMessages(0);
    
    // Messages will be fetched from backend by useEffect when activeSection changes to 'chat'
    // No need to manually restore here
    
    // Save UI state
    if (selectedPatient) {
      const stateToSave = {
        patientId: selectedPatient.patientId,
        activeSection: 'chat',
        isChatMinimized: false,
        isMinimized: isGenerativeAIMinimized
      };
      localStorage.setItem('generativeAIState', JSON.stringify(stateToSave));
    }
  }, [selectedPatient, isGenerativeAIMinimized]);

  // Note: activeSection is now the primary state for navigation
  // No need for activeCategory mapping as we use activeSection directly

  // Track unread messages when chat is minimized
  useEffect(() => {
    if (isChatMinimized && messages.length > 0) {
      // Count messages after chat was minimized (simplified - can be enhanced)
      setUnreadMessages(prev => prev + 1);
    }
  }, [messages, isChatMinimized]);

  // Helper to get section label
  const getSectionLabel = (section: SectionType): string => {
    return SECTION_NAV_ITEMS.find(item => item.id === section)?.label || section;
  };

  // Helper to get breadcrumb path
  const getBreadcrumbPath = (): string[] => {
    if (!selectedPatient) return [];
    const sectionLabel = getSectionLabel(activeSection);
    return [selectedPatient.displayName, sectionLabel];
  };

  // Map section to category for summary display
  const sectionToCategory: Record<SectionType, SummaryCategory> = {
    'patients': 'patient_summary',
    'demographics': 'demographics',
    'observations': 'observations',
    'conditions': 'conditions',
    'notes': 'notes',
    'care_plans': 'care_plans',
    'chat': 'generative_ai'
  };

  // If not on generative-ai route, don't render content
  // User can navigate to other pages normally via sidebar
  // When user clicks "Generative AI" in sidebar, route changes and state restores
  if (router.pathname !== '/generative-ai') {
    return null; // Let Next.js router handle navigation to other pages
  }

  // If minimized (but on generative-ai route), navigate to dashboard
  // This happens when user explicitly minimizes
  // Restore via sidebar "Generative AI" click (which triggers route change and restore)
  useEffect(() => {
    if (isGenerativeAIMinimized && router.pathname === '/generative-ai') {
      // Small delay to allow state to update before navigation
      const timer = setTimeout(() => {
        router.push('/');
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [isGenerativeAIMinimized, router.pathname]);
  
  if (isGenerativeAIMinimized && router.pathname === '/generative-ai') {
    return null; // Will navigate away via useEffect
  }

  // Full-screen Generative AI interface
  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar />

      <div className="flex-1 flex flex-col">
        {/* Header with Minimize/Close */}
        <div className="flex items-center justify-between px-6 py-4 bg-white border-b border-slate-200 shadow-sm">
          <div className="flex items-center gap-3">
            <Sparkles className="text-sidebar-accent" size={20} />
            <h2 className="text-xl font-semibold text-slate-900">Generative AI Assistant</h2>
            </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleMinimizeGenerativeAI}
              className="p-2 rounded-lg hover:bg-slate-100 text-slate-600 hover:text-slate-900 transition"
              title="Minimize Generative AI"
            >
              <Minimize2 size={18} />
            </button>
            <button
              onClick={handleCloseGenerativeAI}
              className="p-2 rounded-lg hover:bg-slate-100 text-slate-600 hover:text-slate-900 transition"
              title="Close Generative AI"
            >
              <X size={18} />
            </button>
                </div>
                </div>
                
        {/* Main Content Area */}
        <div className="flex-1 flex overflow-hidden">
          {/* Left Sidebar Navigation */}
          <aside className="w-64 bg-white border-r border-slate-200 overflow-y-auto">
            <div className="p-4 space-y-6">
              {/* Patient Registry Section */}
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <ShieldCheck className="text-sidebar-accent" size={18} />
                  <h3 className="text-sm font-semibold text-slate-800">Patient Registry</h3>
                </div>
                <div className="relative mb-3">
                  <Search className="absolute left-2 top-2.5 text-slate-400" size={14} />
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Search patients…"
                    className="w-full rounded-lg border border-slate-200 bg-slate-50 pl-7 pr-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-sidebar-accent focus:bg-white"
                  />
                </div>
                <div className="max-h-[200px] overflow-y-auto space-y-1">
                  {patientsLoading && <SummarySkeleton />}
                  {!patientsLoading && patientsError && (
                    <div className="text-xs text-red-600 bg-red-50 border border-red-100 p-2 rounded-lg">
                      {patientsError}
                    </div>
                  )}
                  {!patientsLoading && !patientsError && filteredPatients.map((patient) => {
                    const isActive = selectedPatient?.patientId === patient.patientId;
                    return (
                      <button
                        key={patient.patientId}
                        type="button"
                        onClick={() => handleSelectPatient(patient)}
                        className={`w-full text-left px-2 py-2 rounded-lg border text-xs transition ${
                          isActive
                            ? 'border-sidebar-accent bg-sidebar-accent/10 text-sidebar-accent font-medium'
                            : 'border-slate-200 bg-white text-slate-600 hover:border-sidebar-accent/60'
                        }`}
                      >
                        <div className="font-semibold truncate">{patient.displayName}</div>
                        <div className="text-[10px] text-slate-400 mt-0.5">{patient.patientId}</div>
                      </button>
                    );
                  })}
                </div>
                </div>
                
              {/* Section Navigation */}
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <Wand2 className="text-sidebar-accent" size={18} />
                  <h3 className="text-sm font-semibold text-slate-800">Sections</h3>
                </div>
                <nav className="space-y-1">
                  {SECTION_NAV_ITEMS.map((item) => {
                    const Icon = item.icon;
                    const isActive = activeSection === item.id;
                    const isChat = item.id === 'chat';
                    
                    return (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => {
                          if (isChat && isChatMinimized) {
                            handleMaximizeChat();
                          } else {
                            handleSectionChange(item.id);
                          }
                        }}
                        disabled={!selectedPatient && !isChat}
                        className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition relative ${
                          isActive
                            ? 'bg-sidebar-accent text-white font-medium'
                            : 'text-slate-600 hover:bg-slate-100'
                        } ${!selectedPatient && !isChat ? 'opacity-50 cursor-not-allowed' : ''}`}
                        >
                          <Icon size={16} />
                        <span>{item.label}</span>
                        {isChat && isChatMinimized && (
                          <motion.div
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            className="ml-auto flex items-center gap-1"
                            title="AI Chat minimized - Click to restore"
                          >
                            <div className="w-2 h-2 bg-yellow-400 rounded-full" />
                            {unreadMessages > 0 && (
                              <span className="bg-red-500 text-white text-xs px-1.5 py-0.5 rounded-full">
                                {unreadMessages}
                              </span>
                            )}
                          </motion.div>
                        )}
                      </button>
                    );
                  })}
                </nav>
                </div>

              {/* Refresh Button */}
              {selectedPatient && (
                <div>
                    <button
                      type="button"
                      onClick={() => generateSummaries(selectedPatient.patientId)}
                      disabled={isGeneratingSummaries}
                    className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-sidebar-accent hover:bg-sidebar-accent-hover text-white px-3 py-2 text-xs font-medium transition disabled:opacity-60"
                    >
                      {isGeneratingSummaries ? (
                        <>
                        <Loader2 className="animate-spin" size={14} />
                          <span>Generating...</span>
                        </>
                      ) : (
                        <>
                        <RefreshCw size={14} />
                        <span>Refresh Summaries</span>
                        </>
                      )}
                    </button>
                  </div>
              )}
                </div>
          </aside>

          {/* Center Panel */}
          <main className="flex-1 flex flex-col overflow-hidden bg-slate-50">
            {/* Breadcrumb Navigation */}
                    {selectedPatient && (
              <div className="px-6 py-3 bg-white border-b border-slate-200">
                <div className="flex items-center gap-2 text-sm text-slate-600">
                  {getBreadcrumbPath().map((item, idx) => (
                    <React.Fragment key={idx}>
                      {idx > 0 && <ChevronRight size={14} className="text-slate-400" />}
                      <span className={idx === getBreadcrumbPath().length - 1 ? 'font-semibold text-slate-900' : ''}>
                        {item}
                      </span>
                    </React.Fragment>
                  ))}
                </div>
                  </div>
            )}

            {/* Center Panel Content */}
            <div className={`flex-1 ${activeSection === 'chat' && !isChatMinimized ? 'overflow-hidden' : 'overflow-y-auto'} p-6`}>
              {activeSection === 'chat' && !isChatMinimized ? (
                /* Chat Interface */
                <div className="flex flex-col h-full max-w-5xl mx-auto overflow-hidden">
                  {/* Chat Header */}
                  <div className="flex items-center justify-between mb-4 pb-4 border-b border-slate-200 flex-shrink-0">
                    <h3 className="text-lg font-semibold text-slate-900">AI Chat Interface</h3>
                    <div className="flex items-center gap-2">
                  <button
                        onClick={handleMinimizeChat}
                        className="p-2 rounded-lg hover:bg-slate-100 text-slate-600"
                        title="Minimize Chat"
                      >
                        <Minimize2 size={16} />
                  </button>
                    <button
                        onClick={handleCloseChat}
                        className="p-2 rounded-lg hover:bg-slate-100 text-slate-600"
                        title="Close Chat"
                    >
                      <X size={16} />
                    </button>
                  </div>
                </div>

                  {/* Chat Messages */}
                  <div className="flex-1 overflow-y-auto overflow-x-hidden space-y-4 mb-4 min-h-0">
                  {messages.map((message) => (
                    <div key={message.id} className="space-y-3">
                      {/* Message Bubble */}
                      <div
                        className={`rounded-2xl border px-4 py-3 text-sm shadow-sm ${
                          message.sender === 'user'
                            ? 'bg-sidebar-accent text-white border-transparent ml-auto max-w-[85%]'
                            : 'bg-slate-50 border-slate-200 text-slate-700 max-w-[92%]'
                        }`}
                      >
                        {message.isLoading && (
                          <div className="flex items-center gap-2">
                            <Loader2 className="animate-spin" size={16} />
                            <span>{message.text}</span>
                          </div>
                        )}
                        {!message.isLoading && message.text && (
                            <div className="whitespace-pre-wrap leading-relaxed">
                            {formatLLMResponse(message.text)}
                          </div>
                        )}
                        {!message.isLoading && message.sources && message.sources.length > 0 && (
                          <div className="mt-3 pt-3 border-t border-slate-200">
                            <div className="flex items-center gap-2 mb-2">
                              <Search size={14} className="text-sidebar-accent" />
                                <span className="text-xs font-semibold text-slate-600 uppercase">
                                RAG Sources ({message.sources.length})
                              </span>
                            </div>
                            <div className="space-y-1.5 max-h-32 overflow-y-auto">
                              {message.sources.map((source, idx) => (
                                  <button
                                    key={source.id || idx}
                                    onClick={() => source.id && handleSourceClick(source.id)}
                                    disabled={!source.id || loadingSourceDetail}
                                    className={`text-xs text-left w-full bg-slate-100 rounded-lg px-2.5 py-1.5 border border-slate-200 transition ${
                                      source.id
                                        ? 'hover:bg-sidebar-accent/10 hover:border-sidebar-accent/40 cursor-pointer'
                                        : 'cursor-default opacity-75'
                                    }`}
                                >
                                  <span className="font-medium text-slate-600 capitalize">{source.type}:</span>{' '}
                                  <span className="text-slate-600">{source.description}</span>
                                    {source.id && (
                                      <span className="ml-1 text-sidebar-accent text-[10px]">(click for details)</span>
                                    )}
                                  </button>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                      
                        {/* Chart */}
                      {!message.isLoading && message.chart && (
                        <div className="w-full">
                          {message.chart && typeof message.chart === 'object' && 'type' in message.chart && message.chart.type === 'categorized_observations' && 'charts' in message.chart ? (
                            <div className="space-y-6">
                              {(message.chart as any).charts.map((categoryChart: any, idx: number) => (
                                <motion.div
                                  key={idx}
                                  initial={{ opacity: 0, y: 20 }}
                                  animate={{ opacity: 1, y: 0 }}
                                  transition={{ delay: idx * 0.1 }}
                                  className="bg-white rounded-xl border-2 border-slate-200 p-4 shadow-sm"
                                >
                                  <h4 className="text-lg font-semibold text-slate-800 mb-3">
                                    {categoryChart.category_display}
                                    <span className="ml-2 text-sm text-slate-500 font-normal">
                                      ({categoryChart.observation_count} observation{categoryChart.observation_count !== 1 ? 's' : ''})
                                    </span>
                                  </h4>
                                  <RechartsVisualization 
                                    chart={categoryChart.chart}
                                      title={categoryChart.category_display}
                                  />
                                </motion.div>
                              ))}
                              {(message.chart as any).single_value_observations && (message.chart as any).single_value_observations.length > 0 && (
                                <motion.div
                                  initial={{ opacity: 0, y: 20 }}
                                  animate={{ opacity: 1, y: 0 }}
                                    className="bg-white rounded-xl border-2 border-slate-200 p-4 shadow-sm"
                                >
                                  <h4 className="text-md font-semibold text-slate-700 mb-3">Single-Value Observations</h4>
                                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                                    {(message.chart as any).single_value_observations.map((obs: any, idx: number) => (
                                      <div key={idx} className="bg-white rounded-lg p-2 border border-slate-200">
                                        <div className="text-xs text-slate-500">{obs.display}</div>
                                        <div className="text-sm font-semibold text-slate-800">
                                          {obs.value} {obs.unit ? obs.unit : ''}
                                        </div>
                                        {obs.date && (
                                          <div className="text-xs text-slate-400 mt-1">{new Date(obs.date).toLocaleDateString()}</div>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                </motion.div>
                              )}
                            </div>
                          ) : (
                            <RechartsVisualization 
                              chart={message.chart as ChartPayload}
                              title={(message.chart as ChartPayload).options && typeof (message.chart as ChartPayload).options === 'object' && 'title' in (message.chart as ChartPayload).options
                                ? ((message.chart as ChartPayload).options.title as any)?.text
                                : undefined}
                            />
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                  {/* Chat Error */}
                {chatError && (
                    <div className="mb-4">
                    <div className="text-xs text-rose-600 bg-rose-50 border border-rose-100 rounded-xl px-3 py-2">
                      {chatError}
                    </div>
                  </div>
                )}

                  {/* Chat Input */}
                  <div className="border-t border-slate-200 pt-4 space-y-3">
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder={selectedPatient ? 'Ask about this patient\'s data...' : 'Select a patient to enable chat'}
                      value={chatInput}
                        onChange={(e) => setChatInput(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' && chatInput.trim() && selectedPatient) {
                            e.preventDefault();
                            void sendChatMessage(chatInput);
                        }
                      }}
                      className="flex-1 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sidebar-accent focus:bg-white"
                      disabled={!selectedPatient || chatLoading}
                    />
                    <button
                      type="button"
                      onClick={() => {
                          if (chatInput.trim() && selectedPatient) {
                          void sendChatMessage(chatInput);
                        }
                      }}
                      className="inline-flex items-center gap-2 rounded-xl bg-sidebar-accent hover:bg-sidebar-accent-hover text-white px-4 py-2 text-sm font-medium transition disabled:opacity-60"
                      disabled={!selectedPatient || chatLoading}
                    >
                      {chatLoading ? <Loader2 className="animate-spin" size={16} /> : <SendIcon />}
                      <span>Send</span>
                    </button>
                  </div>

                    {/* Follow-up Options */}
                  <AnimatePresence>
                    {followUpOptions.length > 0 && (
                      <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="bg-slate-50 border border-slate-200 rounded-2xl p-4 space-y-2"
                      >
                        <div className="text-xs font-semibold text-slate-500 uppercase">Suggested follow-ups</div>
                        <div className="flex flex-wrap gap-2">
                          {followUpOptions.map((option, index) => (
                            <button
                              key={`${option.text}-${index}`}
                              type="button"
                              onClick={() => handleFollowUp(option)}
                              className="inline-flex items-center gap-2 rounded-full bg-white border border-sidebar-accent/40 text-sidebar-accent text-xs px-3 py-1 font-medium hover:bg-sidebar-accent/10"
                            >
                              <ArrowRight size={14} />
                              {option.text.replace(/^[^\w]+/g, '')}
                            </button>
                          ))}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </div>
              ) : !selectedPatient ? (
                /* Welcome Screen */
                <div className="max-w-4xl mx-auto">
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="text-center py-12"
                  >
                    <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-gradient-to-br from-sidebar-accent/20 to-sidebar-accent-hover/20 mb-6">
                      <Sparkles className="text-sidebar-accent" size={32} />
                    </div>
                    <h2 className="text-3xl font-bold text-slate-900 mb-3">Welcome to Generative AI Assistant</h2>
                    <p className="text-slate-600 mb-8 max-w-2xl mx-auto">
                      Select a patient to view AI-generated summaries, or start a chat to ask questions about their medical data.
                    </p>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-8">
      <motion.button
                        whileHover={{ y: -2, scale: 1.02 }}
                        onClick={() => handleSectionChange('patients')}
                        className="p-6 rounded-xl border-2 border-slate-200 bg-white hover:border-sidebar-accent/60 hover:shadow-lg transition text-left"
                      >
                        <Users className="text-sidebar-accent mb-3" size={24} />
                        <h3 className="font-semibold text-slate-900 mb-1">Browse Patients</h3>
                        <p className="text-xs text-slate-500">Select a patient from the sidebar</p>
      </motion.button>

                      <motion.button
                        whileHover={{ y: -2, scale: 1.02 }}
                        onClick={() => handleSectionChange('chat')}
                        className="p-6 rounded-xl border-2 border-slate-200 bg-white hover:border-sidebar-accent/60 hover:shadow-lg transition text-left"
                      >
                        <Bot className="text-sidebar-accent mb-3" size={24} />
                        <h3 className="font-semibold text-slate-900 mb-1">Start AI Chat</h3>
                        <p className="text-xs text-slate-500">Ask questions about medical data</p>
                      </motion.button>

                      <motion.div
                        className="p-6 rounded-xl border-2 border-slate-200 bg-white"
                      >
                        <Sparkles className="text-sidebar-accent mb-3" size={24} />
                        <h3 className="font-semibold text-slate-900 mb-1">AI Summaries</h3>
                        <p className="text-xs text-slate-500">View patient summaries and insights</p>
                      </motion.div>
                    </div>
                  </motion.div>
                </div>
              ) : (
                /* Section Summary Display */
                <div className="max-w-5xl mx-auto">
                  {isGeneratingSummaries && activeSection !== 'chat' && <SummaryCardSkeleton />}
                  {!isGeneratingSummaries && summaryError && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="flex items-center gap-3 text-sm text-rose-600 bg-rose-50 border-2 border-rose-200 p-4 rounded-2xl"
                    >
                      <AlertCircle size={18} />
                      <span className="font-medium">{summaryError}</span>
                    </motion.div>
                  )}
                  {!isGeneratingSummaries && !summaryError && displayedSummary && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.4 }}
                      className="bg-white rounded-2xl border-2 border-slate-200 p-6 lg:p-8 shadow-sm"
                    >
                      <div className="text-slate-700 leading-relaxed prose prose-slate max-w-none">
                        {formatLLMResponse(displayedSummary)}
                      </div>
                    </motion.div>
                  )}
                  {!isGeneratingSummaries && !summaryError && !displayedSummary && activeSection !== 'chat' && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="text-center py-12"
                    >
                      <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-slate-100 mb-4">
                        <Sparkles className="text-slate-400" size={24} />
                      </div>
                      <p className="text-slate-500 font-medium">Generating summary...</p>
                    </motion.div>
                  )}
                </div>
              )}
            </div>

            {/* Minimized Chat Bar */}
            {isChatMinimized && (
              <motion.div
                initial={{ y: 100 }}
                animate={{ y: 0 }}
                className="fixed bottom-0 left-64 right-0 h-16 bg-white border-t border-slate-200 shadow-lg flex items-center justify-between px-6 z-50"
              >
                <div className="flex items-center gap-3">
                  <Bot className="text-sidebar-accent" size={20} />
                  <span className="text-sm font-medium text-slate-700">AI Chat Interface</span>
                  {unreadMessages > 0 && (
                    <span className="bg-red-500 text-white text-xs px-2 py-1 rounded-full">
                      {unreadMessages} new
                    </span>
                  )}
                </div>
                <button
                  onClick={handleMaximizeChat}
                  className="text-sm text-sidebar-accent hover:text-sidebar-accent-hover font-medium flex items-center gap-1"
                  title="Maximize chat"
                >
                  <Maximize2 size={14} />
                </button>
              </motion.div>
            )}
          </main>
        </div>
      </div>

      {/* Source Detail Modal */}
      <SourceDetailModal
        source={selectedSource}
        open={sourceModalOpen}
        onOpenChange={setSourceModalOpen}
      />
    </div>
  );
}

function ClockIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      className="w-3.5 h-3.5"
    >
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="currentColor"
      className="w-4 h-4"
    >
      <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
    </svg>
  );
}
