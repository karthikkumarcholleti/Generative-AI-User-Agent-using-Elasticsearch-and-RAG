import React, { useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, Search, ArrowRight, Minimize2, X } from 'lucide-react';
import { formatLLMResponse } from '@/components/shared/LLMResponseFormatter';
import RechartsVisualization from '@/components/RechartsVisualization';
import SourceDetailModal from '@/components/SourceDetailModal';
import type { ChatMessage } from '@/hooks/usePatientChat';
import type { FollowUpOption, ChartPayload } from '@/services/llmApi';

interface ChatPanelProps {
  messages: ChatMessage[];
  loading: boolean;
  error: string | null;
  chatInput: string;
  setChatInput: (v: string) => void;
  followUpOptions: FollowUpOption[];
  onSend: (text: string) => void;
  onFollowUp: (option: FollowUpOption) => void;
  onSourceClick: (sourceId: string) => void;
  selectedSource: any;
  sourceModalOpen: boolean;
  setSourceModalOpen: (open: boolean) => void;
  loadingSource: boolean;
  disabled: boolean;
  onMinimize?: () => void;
  onClose?: () => void;
}

function SendIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
      <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
    </svg>
  );
}

export default function ChatPanel({
  messages,
  loading,
  error,
  chatInput,
  setChatInput,
  followUpOptions,
  onSend,
  onFollowUp,
  onSourceClick,
  selectedSource,
  sourceModalOpen,
  setSourceModalOpen,
  loadingSource,
  disabled,
  onMinimize,
  onClose,
}: ChatPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div className="flex flex-col h-full max-w-5xl mx-auto overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 pb-4 border-b border-slate-200 flex-shrink-0">
        <h3 className="text-lg font-semibold text-slate-900">AI Chat Interface</h3>
        <div className="flex items-center gap-2">
          {onMinimize && (
            <button onClick={onMinimize} className="p-2 rounded-lg hover:bg-slate-100 text-slate-600" title="Minimize Chat">
              <Minimize2 size={16} />
            </button>
          )}
          {onClose && (
            <button onClick={onClose} className="p-2 rounded-lg hover:bg-slate-100 text-slate-600" title="Close Chat">
              <X size={16} />
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto overflow-x-hidden space-y-4 mb-4 min-h-0">
        {messages.map(message => (
          <div key={message.id} className="space-y-3">
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
                        onClick={() => source.id && onSourceClick(source.id)}
                        disabled={!source.id || loadingSource}
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
                {typeof message.chart === 'object' && 'type' in message.chart && message.chart.type === 'categorized_observations' && 'charts' in message.chart ? (
                  <div className="space-y-6">
                    {(message.chart as any).charts.map((cat: any, idx: number) => (
                      <motion.div
                        key={idx}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: idx * 0.1 }}
                        className="bg-white rounded-xl border-2 border-slate-200 p-4 shadow-sm"
                      >
                        <h4 className="text-lg font-semibold text-slate-800 mb-3">
                          {cat.category_display}
                          <span className="ml-2 text-sm text-slate-500 font-normal">
                            ({cat.observation_count} observation{cat.observation_count !== 1 ? 's' : ''})
                          </span>
                        </h4>
                        <RechartsVisualization chart={cat.chart} title={cat.category_display} />
                      </motion.div>
                    ))}
                    {(message.chart as any).single_value_observations?.length > 0 && (
                      <div className="bg-white rounded-xl border-2 border-slate-200 p-4 shadow-sm">
                        <h4 className="text-md font-semibold text-slate-700 mb-3">Single-Value Observations</h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                          {(message.chart as any).single_value_observations.map((obs: any, idx: number) => (
                            <div key={idx} className="bg-white rounded-lg p-2 border border-slate-200">
                              <div className="text-xs text-slate-500">{obs.display}</div>
                              <div className="text-sm font-semibold text-slate-800">
                                {obs.value}{obs.unit ? ` ${obs.unit}` : ''}
                              </div>
                              {obs.date && (
                                <div className="text-xs text-slate-400 mt-1">
                                  {new Date(obs.date).toLocaleDateString()}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
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

      {/* Error */}
      {error && (
        <div className="mb-4">
          <div className="text-xs text-rose-600 bg-rose-50 border border-rose-100 rounded-xl px-3 py-2">{error}</div>
        </div>
      )}

      {/* Input */}
      <div className="border-t border-slate-200 pt-4 space-y-3 flex-shrink-0">
        <div className="flex gap-2">
          <input
            type="text"
            placeholder={disabled ? 'Select a patient to enable chat' : 'Ask about this patient\'s data...'}
            value={chatInput}
            onChange={e => setChatInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && chatInput.trim() && !disabled) {
                e.preventDefault();
                onSend(chatInput);
              }
            }}
            className="flex-1 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sidebar-accent focus:bg-white"
            disabled={disabled || loading}
          />
          <button
            type="button"
            onClick={() => { if (chatInput.trim() && !disabled) onSend(chatInput); }}
            className="inline-flex items-center gap-2 rounded-xl bg-sidebar-accent hover:bg-sidebar-accent-hover text-white px-4 py-2 text-sm font-medium transition disabled:opacity-60"
            disabled={disabled || loading}
          >
            {loading ? <Loader2 className="animate-spin" size={16} /> : <SendIcon />}
            <span>Send</span>
          </button>
        </div>

        {/* Follow-up options */}
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
                {followUpOptions.map((option, i) => (
                  <button
                    key={`${option.text}-${i}`}
                    type="button"
                    onClick={() => onFollowUp(option)}
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

      <SourceDetailModal source={selectedSource} open={sourceModalOpen} onOpenChange={setSourceModalOpen} />
    </div>
  );
}
