import React, { useMemo, useState } from 'react';
import { Search, ShieldCheck } from 'lucide-react';
import { motion } from 'framer-motion';
import type { PatientLite } from '@/services/llmApi';

interface PatientSelectorProps {
  patients: PatientLite[];
  loading: boolean;
  error: string | null;
  selected: PatientLite | null;
  onSelect: (patient: PatientLite) => void;
}

function SelectorSkeleton() {
  return (
    <div className="space-y-2">
      {[1, 2, 3].map(i => (
        <div key={i} className="h-12 bg-slate-100 rounded-lg animate-pulse" />
      ))}
    </div>
  );
}

export default function PatientSelector({ patients, loading, error, selected, onSelect }: PatientSelectorProps) {
  const [searchTerm, setSearchTerm] = useState('');

  const filtered = useMemo(() => {
    if (!searchTerm.trim()) return patients;
    const term = searchTerm.toLowerCase();
    return patients.filter(p =>
      p.patientId.toLowerCase().includes(term) ||
      p.displayName.toLowerCase().includes(term)
    );
  }, [patients, searchTerm]);

  return (
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
          onChange={e => setSearchTerm(e.target.value)}
          placeholder="Search patients…"
          className="w-full rounded-lg border border-slate-200 bg-slate-50 pl-7 pr-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-sidebar-accent focus:bg-white"
        />
      </div>

      <div className="max-h-[200px] overflow-y-auto space-y-1">
        {loading && <SelectorSkeleton />}
        {!loading && error && (
          <div className="text-xs text-red-600 bg-red-50 border border-red-100 p-2 rounded-lg">{error}</div>
        )}
        {!loading && !error && filtered.map(patient => {
          const isActive = selected?.patientId === patient.patientId;
          return (
            <button
              key={patient.patientId}
              type="button"
              onClick={() => onSelect(patient)}
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
  );
}
