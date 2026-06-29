import React, { useState, useCallback, useEffect, useRef } from 'react';
import { useRouter } from 'next/router';
import { motion } from 'framer-motion';
import {
  Bot,
  ClipboardList,
  RefreshCw,
  Sparkles,
  Stethoscope,
  Activity,
  BookOpenCheck,
  Brain,
  ShieldCheck,
  Wand2,
  X,
  Minimize2,
  Maximize2,
  Users,
  ChevronRight,
  BarChart3,
} from 'lucide-react';
import Sidebar from '@/components/Sidebar';
import PatientSelector from '@/components/patient/PatientSelector';
import SummaryPanel from '@/components/patient/SummaryPanel';
import ChatPanel from '@/components/patient/ChatPanel';
import CohortSelector from '@/components/population/CohortSelector';
import PopulationChat from '@/components/population/PopulationChat';
import { usePatients } from '@/hooks/usePatients';
import { usePatientSummary } from '@/hooks/usePatientSummary';
import { usePatientChat } from '@/hooks/usePatientChat';
import { deleteConversation } from '@/services/llmApi';
import type { PatientLite } from '@/services/llmApi';

type Mode = 'patient' | 'population';
type SectionType = 'patients' | 'demographics' | 'observations' | 'conditions' | 'notes' | 'care_plans' | 'chat';

const SECTION_NAV: Array<{ id: SectionType; label: string; icon: React.ComponentType<{ size?: number }> }> = [
  { id: 'patients',    label: 'Patients',         icon: Users },
  { id: 'demographics',label: 'Demographics',      icon: ClipboardList },
  { id: 'observations',label: 'Observations',      icon: Activity },
  { id: 'conditions',  label: 'Conditions',        icon: Stethoscope },
  { id: 'notes',       label: 'Notes',             icon: BookOpenCheck },
  { id: 'care_plans',  label: 'Care Plans',        icon: Brain },
  { id: 'chat',        label: 'AI Chat Interface', icon: Bot },
];

export default function GenerativeAIPage() {
  const router = useRouter();

  // Mode toggle — Patient-level vs Population-level
  const [mode, setMode] = useState<Mode>('patient');

  // Shared patient data
  const { patients, loading: patientsLoading, error: patientsError } = usePatients();

  // Patient-level state
  const [selectedPatient, setSelectedPatient] = useState<PatientLite | null>(null);
  const [activeSection, setActiveSection] = useState<SectionType>('patients');
  const [isChatMinimized, setIsChatMinimized] = useState(false);
  const [unreadMessages, setUnreadMessages] = useState(0);
  const [isMinimized, setIsMinimized] = useState(false);

  // Patient summary + chat hooks
  const { summaries, loading: summaryLoading, error: summaryError, refresh: refreshSummaries } = usePatientSummary(selectedPatient?.patientId ?? null);
  const chat = usePatientChat(selectedPatient);

  // Population-level state
  const [selectedCohortIds, setSelectedCohortIds] = useState<string[]>([]);

  // Refs to avoid stale closures in router event handlers
  const selectedPatientRef = useRef(selectedPatient);
  const activeSectionRef = useRef(activeSection);
  const isChatMinimizedRef = useRef(isChatMinimized);
  useEffect(() => { selectedPatientRef.current = selectedPatient; }, [selectedPatient]);
  useEffect(() => { activeSectionRef.current = activeSection; }, [activeSection]);
  useEffect(() => { isChatMinimizedRef.current = isChatMinimized; }, [isChatMinimized]);

  // Restore from localStorage + URL on mount
  useEffect(() => {
    if (router.pathname !== '/generative-ai') return;
    const saved = localStorage.getItem('generativeAIState');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (parsed.mode) setMode(parsed.mode);
        if (parsed.isChatMinimized !== undefined) setIsChatMinimized(parsed.isChatMinimized);
        if (parsed.isMinimized) { setIsMinimized(true); return; }

        const patientIdToRestore = (router.query.patientId as string) || (parsed.summariesGenerated ? parsed.patientId : null);
        if (patientIdToRestore && patients.length > 0 && !selectedPatient) {
          const patient = patients.find(p => p.patientId === patientIdToRestore);
          if (patient) {
            setSelectedPatient(patient);
            setActiveSection(parsed.activeSection || 'patients');
          }
        }
      } catch {}
    }
  }, [patients, router.query.patientId, router.pathname]);

  // Save state to localStorage when it changes
  useEffect(() => {
    if (!selectedPatient) return;
    const state = { patientId: selectedPatient.patientId, activeSection, isChatMinimized, mode, summariesGenerated: Object.keys(summaries).length > 0 };
    localStorage.setItem('generativeAIState', JSON.stringify(state));
    // Sync URL
    if ((router.query.patientId as string) !== selectedPatient.patientId) {
      router.replace({ pathname: router.pathname, query: { ...router.query, patientId: selectedPatient.patientId } }, undefined, { shallow: true });
    }
  }, [selectedPatient, activeSection, isChatMinimized, mode, summaries]);

  // Auto-minimize when navigating away
  useEffect(() => {
    const handleRoute = (url: string) => {
      if (!url.includes('/generative-ai')) {
        setIsMinimized(true);
        const patient = selectedPatientRef.current;
        if (patient) {
          const state = { patientId: patient.patientId, activeSection: activeSectionRef.current, isChatMinimized: isChatMinimizedRef.current, isMinimized: true };
          localStorage.setItem('generativeAIState', JSON.stringify(state));
        }
      }
    };
    router.events?.on('routeChangeStart', handleRoute);
    return () => router.events?.off('routeChangeStart', handleRoute);
  }, [router]);

  // Navigate away when minimized
  useEffect(() => {
    if (isMinimized && router.pathname === '/generative-ai') {
      const t = setTimeout(() => router.push('/'), 100);
      return () => clearTimeout(t);
    }
  }, [isMinimized, router.pathname]);

  // Track unread messages when chat is minimized
  useEffect(() => {
    if (isChatMinimized && chat.messages.length > 0) {
      setUnreadMessages(n => n + 1);
    }
  }, [chat.messages, isChatMinimized]);

  const handleSelectPatient = useCallback(async (patient: PatientLite) => {
    if (selectedPatient?.patientId === patient.patientId) return;
    try { await deleteConversation(patient.patientId); } catch {}
    setSelectedPatient(patient);
    setActiveSection('patients');
    setIsChatMinimized(false);
  }, [selectedPatient]);

  const handleSectionChange = useCallback((section: SectionType) => {
    setActiveSection(section);
    if (section === 'chat') setIsChatMinimized(false);
  }, []);

  const getBreadcrumb = (): string[] => {
    if (!selectedPatient) return [];
    const label = SECTION_NAV.find(s => s.id === activeSection)?.label || activeSection;
    return [selectedPatient.displayName, label];
  };

  if (router.pathname !== '/generative-ai') return null;
  if (isMinimized) return null;

  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar />

      <div className="flex-1 flex flex-col">
        {/* Top Header */}
        <div className="flex items-center justify-between px-6 py-4 bg-white border-b border-slate-200 shadow-sm">
          <div className="flex items-center gap-3">
            <Sparkles className="text-sidebar-accent" size={20} />
            <h2 className="text-xl font-semibold text-slate-900">Generative AI Assistant</h2>
          </div>

          {/* Mode Toggle */}
          <div className="flex items-center gap-2 bg-slate-100 rounded-lg p-1">
            <button
              onClick={() => setMode('patient')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition ${
                mode === 'patient'
                  ? 'bg-white text-sidebar-accent shadow-sm'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              <ShieldCheck size={15} />
              Patient Level
            </button>
            <button
              onClick={() => setMode('population')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition ${
                mode === 'population'
                  ? 'bg-white text-sidebar-accent shadow-sm'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              <BarChart3 size={15} />
              Population Level
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsMinimized(true)}
              className="p-2 rounded-lg hover:bg-slate-100 text-slate-600 hover:text-slate-900 transition"
              title="Minimize"
            >
              <Minimize2 size={18} />
            </button>
            <button
              onClick={() => router.push('/')}
              className="p-2 rounded-lg hover:bg-slate-100 text-slate-600 hover:text-slate-900 transition"
              title="Close"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex overflow-hidden">

          {/* Left Sidebar */}
          <aside className="w-64 bg-white border-r border-slate-200 overflow-y-auto">
            <div className="p-4 space-y-6">

              {mode === 'patient' ? (
                <>
                  {/* Patient Registry */}
                  <PatientSelector
                    patients={patients}
                    loading={patientsLoading}
                    error={patientsError}
                    selected={selectedPatient}
                    onSelect={handleSelectPatient}
                  />

                  {/* Section Navigation */}
                  <div>
                    <div className="flex items-center gap-2 mb-3">
                      <Wand2 className="text-sidebar-accent" size={18} />
                      <h3 className="text-sm font-semibold text-slate-800">Sections</h3>
                    </div>
                    <nav className="space-y-1">
                      {SECTION_NAV.map(item => {
                        const Icon = item.icon;
                        const isActive = activeSection === item.id;
                        const isChat = item.id === 'chat';
                        return (
                          <button
                            key={item.id}
                            type="button"
                            onClick={() => {
                              if (isChat && isChatMinimized) {
                                setIsChatMinimized(false);
                                setUnreadMessages(0);
                                setActiveSection('chat');
                              } else {
                                handleSectionChange(item.id);
                              }
                            }}
                            disabled={!selectedPatient && !isChat}
                            className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition relative ${
                              isActive ? 'bg-sidebar-accent text-white font-medium' : 'text-slate-600 hover:bg-slate-100'
                            } ${!selectedPatient && !isChat ? 'opacity-50 cursor-not-allowed' : ''}`}
                          >
                            <Icon size={16} />
                            <span>{item.label}</span>
                            {isChat && isChatMinimized && (
                              <div className="ml-auto flex items-center gap-1">
                                <div className="w-2 h-2 bg-yellow-400 rounded-full" />
                                {unreadMessages > 0 && (
                                  <span className="bg-red-500 text-white text-xs px-1.5 py-0.5 rounded-full">
                                    {unreadMessages}
                                  </span>
                                )}
                              </div>
                            )}
                          </button>
                        );
                      })}
                    </nav>
                  </div>

                  {/* Refresh */}
                  {selectedPatient && (
                    <button
                      type="button"
                      onClick={() => refreshSummaries()}
                      disabled={summaryLoading}
                      className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-sidebar-accent hover:bg-sidebar-accent-hover text-white px-3 py-2 text-xs font-medium transition disabled:opacity-60"
                    >
                      {summaryLoading
                        ? <><RefreshCw className="animate-spin" size={14} /><span>Generating...</span></>
                        : <><RefreshCw size={14} /><span>Refresh Summaries</span></>
                      }
                    </button>
                  )}
                </>
              ) : (
                /* Population mode: cohort selector */
                <CohortSelector
                  patients={patients}
                  loading={patientsLoading}
                  selectedIds={selectedCohortIds}
                  onChange={setSelectedCohortIds}
                />
              )}
            </div>
          </aside>

          {/* Center Panel */}
          <main className="flex-1 flex flex-col overflow-hidden bg-slate-50">

            {/* Breadcrumb (patient mode only) */}
            {mode === 'patient' && selectedPatient && (
              <div className="px-6 py-3 bg-white border-b border-slate-200">
                <div className="flex items-center gap-2 text-sm text-slate-600">
                  {getBreadcrumb().map((item, idx, arr) => (
                    <React.Fragment key={idx}>
                      {idx > 0 && <ChevronRight size={14} className="text-slate-400" />}
                      <span className={idx === arr.length - 1 ? 'font-semibold text-slate-900' : ''}>{item}</span>
                    </React.Fragment>
                  ))}
                </div>
              </div>
            )}

            {/* Population mode header */}
            {mode === 'population' && (
              <div className="px-6 py-3 bg-white border-b border-slate-200 flex items-center gap-2">
                <BarChart3 size={16} className="text-sidebar-accent" />
                <span className="text-sm font-semibold text-slate-800">Population-Level Analysis</span>
                <span className="text-xs text-slate-500 ml-1">— Ziletti &amp; D'Ambrosi (2025) RAG+A+C</span>
              </div>
            )}

            {/* Content area */}
            <div className={`flex-1 ${activeSection === 'chat' && mode === 'patient' && !isChatMinimized ? 'overflow-hidden' : 'overflow-y-auto'} p-6`}>

              {mode === 'population' ? (
                <PopulationChat selectedPatientIds={selectedCohortIds} />
              ) : activeSection === 'chat' && !isChatMinimized ? (
                <ChatPanel
                  messages={chat.messages}
                  loading={chat.loading}
                  error={chat.error}
                  chatInput={chat.chatInput}
                  setChatInput={chat.setChatInput}
                  followUpOptions={chat.followUpOptions}
                  onSend={chat.send}
                  onFollowUp={chat.handleFollowUp}
                  onSourceClick={chat.handleSourceClick}
                  selectedSource={chat.selectedSource}
                  sourceModalOpen={chat.sourceModalOpen}
                  setSourceModalOpen={chat.setSourceModalOpen}
                  loadingSource={chat.loadingSource}
                  disabled={!selectedPatient}
                  onMinimize={() => { setIsChatMinimized(true); setUnreadMessages(0); }}
                  onClose={() => setActiveSection('patients')}
                />
              ) : !selectedPatient ? (
                /* Welcome screen */
                <div className="max-w-4xl mx-auto">
                  <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center py-12">
                    <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-gradient-to-br from-sidebar-accent/20 to-sidebar-accent-hover/20 mb-6">
                      <Sparkles className="text-sidebar-accent" size={32} />
                    </div>
                    <h2 className="text-3xl font-bold text-slate-900 mb-3">Welcome to Generative AI Assistant</h2>
                    <p className="text-slate-600 mb-8 max-w-2xl mx-auto">
                      Use <strong>Patient Level</strong> for individual EHR queries and summaries, or <strong>Population Level</strong> for cohort analytics.
                    </p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-8 max-w-2xl mx-auto">
                      <motion.button whileHover={{ y: -2 }} onClick={() => setMode('patient')} className="p-6 rounded-xl border-2 border-slate-200 bg-white hover:border-sidebar-accent/60 hover:shadow-lg transition text-left">
                        <ShieldCheck className="text-sidebar-accent mb-3" size={24} />
                        <h3 className="font-semibold text-slate-900 mb-1">Patient Level</h3>
                        <p className="text-xs text-slate-500">Select a patient, view summaries, ask RAG/MedRAG questions</p>
                      </motion.button>
                      <motion.button whileHover={{ y: -2 }} onClick={() => setMode('population')} className="p-6 rounded-xl border-2 border-slate-200 bg-white hover:border-sidebar-accent/60 hover:shadow-lg transition text-left">
                        <BarChart3 className="text-sidebar-accent mb-3" size={24} />
                        <h3 className="font-semibold text-slate-900 mb-1">Population Level</h3>
                        <p className="text-xs text-slate-500">Select a cohort, run analytics queries across the group</p>
                      </motion.button>
                    </div>
                  </motion.div>
                </div>
              ) : (
                /* Section summary display */
                <div className="max-w-5xl mx-auto">
                  <SummaryPanel
                    summaries={summaries}
                    loading={summaryLoading}
                    error={summaryError}
                    activeSection={activeSection}
                  />
                </div>
              )}
            </div>

            {/* Minimized Chat Bar */}
            {isChatMinimized && mode === 'patient' && (
              <motion.div
                initial={{ y: 100 }}
                animate={{ y: 0 }}
                className="fixed bottom-0 left-64 right-0 h-16 bg-white border-t border-slate-200 shadow-lg flex items-center justify-between px-6 z-50"
              >
                <div className="flex items-center gap-3">
                  <Bot className="text-sidebar-accent" size={20} />
                  <span className="text-sm font-medium text-slate-700">AI Chat Interface</span>
                  {unreadMessages > 0 && (
                    <span className="bg-red-500 text-white text-xs px-2 py-1 rounded-full">{unreadMessages} new</span>
                  )}
                </div>
                <button
                  onClick={() => { setIsChatMinimized(false); setActiveSection('chat'); setUnreadMessages(0); }}
                  className="text-sm text-sidebar-accent hover:text-sidebar-accent-hover font-medium flex items-center gap-1"
                >
                  <Maximize2 size={14} />
                </button>
              </motion.div>
            )}
          </main>
        </div>
      </div>
    </div>
  );
}
