import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { AlertCircle, Sparkles } from 'lucide-react';
import { formatLLMResponse } from '@/components/shared/LLMResponseFormatter';
import type { SummaryCategory } from '@/hooks/usePatientSummary';

type SectionType = 'patients' | 'demographics' | 'observations' | 'conditions' | 'notes' | 'care_plans' | 'chat';

const SECTION_TO_CATEGORY: Record<SectionType, SummaryCategory> = {
  patients: 'patient_summary',
  demographics: 'demographics',
  observations: 'observations',
  conditions: 'conditions',
  notes: 'notes',
  care_plans: 'care_plans',
  chat: 'generative_ai',
};

function SummaryCardSkeleton() {
  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
      <div className="h-6 bg-slate-200 rounded w-3/4 animate-pulse" />
      <div className="space-y-2">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="h-4 bg-slate-100 rounded animate-pulse" style={{ width: `${60 + i * 10}%` }} />
        ))}
      </div>
    </motion.div>
  );
}

interface SummaryPanelProps {
  summaries: Partial<Record<SummaryCategory, string>>;
  loading: boolean;
  error: string | null;
  activeSection: SectionType;
}

export default function SummaryPanel({ summaries, loading, error, activeSection }: SummaryPanelProps) {
  const [displayedText, setDisplayedText] = useState('');

  const category = SECTION_TO_CATEGORY[activeSection];
  const rawSummary = category ? summaries[category] : null;

  // Typing animation when summary or section changes
  useEffect(() => {
    if (!rawSummary) {
      setDisplayedText('');
      return;
    }
    setDisplayedText('');
    let index = 0;
    const speed = rawSummary.length > 4000 ? 2 : 6;
    const interval = window.setInterval(() => {
      index += speed;
      setDisplayedText(rawSummary.slice(0, index));
      if (index >= rawSummary.length) window.clearInterval(interval);
    }, 16);
    return () => window.clearInterval(interval);
  }, [rawSummary, activeSection]);

  if (loading) return <SummaryCardSkeleton />;

  if (error) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center gap-3 text-sm text-rose-600 bg-rose-50 border-2 border-rose-200 p-4 rounded-2xl"
      >
        <AlertCircle size={18} />
        <span className="font-medium">{error}</span>
      </motion.div>
    );
  }

  if (displayedText) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="bg-white rounded-2xl border-2 border-slate-200 p-6 lg:p-8 shadow-sm"
      >
        <div className="text-slate-700 leading-relaxed prose prose-slate max-w-none">
          {formatLLMResponse(displayedText)}
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center py-12">
      <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-slate-100 mb-4">
        <Sparkles className="text-slate-400" size={24} />
      </div>
      <p className="text-slate-500 font-medium">Generating summary...</p>
    </motion.div>
  );
}
