import React from 'react';
import { motion } from 'framer-motion';
import { Loader2, Users, Database, Clock, ArrowRight } from 'lucide-react';
import { formatLLMResponse } from '@/components/shared/LLMResponseFormatter';
import { usePopulationQuery } from '@/hooks/usePopulationQuery';

const SAMPLE_QUESTIONS = [
  'What is the average HbA1c across this cohort?',
  'How many patients have uncontrolled hypertension?',
  'Which patients have both diabetes and chronic kidney disease?',
  'What is the most common comorbidity in this group?',
  'Show patients with BMI above 30 and cardiovascular risk',
  'How many patients have been hospitalized in the last 12 months?',
];

interface PopulationChatProps {
  selectedPatientIds: string[];
}

export default function PopulationChat({ selectedPatientIds }: PopulationChatProps) {
  const { response, loading, error, query, setQuery, submit, clear } = usePopulationQuery();

  const hasSelection = selectedPatientIds.length > 0;

  const handleSubmit = () => {
    if (query.trim() && hasSelection) {
      void submit(selectedPatientIds, query);
    }
  };

  return (
    <div className="flex flex-col h-full max-w-5xl mx-auto">
      {/* Cohort status bar */}
      <div className={`flex items-center gap-3 px-4 py-3 rounded-xl mb-6 text-sm ${
        hasSelection
          ? 'bg-sidebar-accent/10 border border-sidebar-accent/30 text-sidebar-accent'
          : 'bg-slate-100 border border-slate-200 text-slate-500'
      }`}>
        <Users size={16} />
        {hasSelection
          ? <span><strong>{selectedPatientIds.length} patients</strong> selected for population analysis</span>
          : <span>Select patients from the cohort panel on the left to begin population analysis</span>
        }
      </div>

      {/* Response area */}
      {response && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-2xl border-2 border-slate-200 p-6 mb-6 shadow-sm space-y-4"
        >
          <div className="flex items-center gap-4 text-xs text-slate-500 pb-3 border-b border-slate-100">
            <span className="flex items-center gap-1">
              <Database size={12} />
              {response.patient_count} patient{response.patient_count !== 1 ? 's' : ''} analyzed
            </span>
            <span className="flex items-center gap-1">
              <Clock size={12} />
              {(response.elapsed_ms / 1000).toFixed(1)}s
            </span>
            <span className="px-2 py-0.5 rounded-full bg-slate-100 font-medium">
              {response.pipeline_mode}
            </span>
          </div>

          <div className="text-slate-700 leading-relaxed prose prose-slate max-w-none">
            {formatLLMResponse(response.response)}
          </div>

          {response.sql_used && (
            <details className="mt-4">
              <summary className="text-xs text-slate-400 cursor-pointer hover:text-slate-600 select-none">
                View generated SQL
              </summary>
              <pre className="mt-2 text-xs bg-slate-50 rounded-lg p-3 border border-slate-200 overflow-x-auto whitespace-pre-wrap text-slate-600">
                {response.sql_used}
              </pre>
            </details>
          )}

          <div className="flex justify-end pt-2">
            <button
              onClick={clear}
              className="text-xs text-slate-400 hover:text-slate-600 transition"
            >
              Clear result
            </button>
          </div>
        </motion.div>
      )}

      {error && (
        <div className="mb-4 text-xs text-rose-600 bg-rose-50 border border-rose-100 rounded-xl px-4 py-3">
          {error}
        </div>
      )}

      {/* Input */}
      <div className="border border-slate-200 rounded-2xl bg-white p-4 space-y-3 shadow-sm">
        <div className="flex gap-2">
          <textarea
            rows={2}
            placeholder={hasSelection ? 'Ask a population-level clinical question...' : 'Select a patient cohort first'}
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey && query.trim() && hasSelection) {
                e.preventDefault();
                handleSubmit();
              }
            }}
            className="flex-1 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sidebar-accent focus:bg-white resize-none"
            disabled={!hasSelection || loading}
          />
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!hasSelection || !query.trim() || loading}
            className="self-end inline-flex items-center gap-2 rounded-xl bg-sidebar-accent hover:bg-sidebar-accent-hover text-white px-4 py-2 text-sm font-medium transition disabled:opacity-50"
          >
            {loading ? <Loader2 className="animate-spin" size={16} /> : <ArrowRight size={16} />}
            <span>Analyze</span>
          </button>
        </div>

        {/* Sample questions */}
        {!response && !loading && (
          <div className="space-y-1">
            <div className="text-xs text-slate-400 font-medium uppercase">Sample questions</div>
            <div className="flex flex-wrap gap-2">
              {SAMPLE_QUESTIONS.map((q, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => { setQuery(q); }}
                  disabled={!hasSelection}
                  className="text-xs bg-slate-50 border border-slate-200 rounded-full px-3 py-1 text-slate-600 hover:border-sidebar-accent/50 hover:text-sidebar-accent transition disabled:opacity-40"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
