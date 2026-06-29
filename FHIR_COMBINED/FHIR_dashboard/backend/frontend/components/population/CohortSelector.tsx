import React, { useMemo, useState } from 'react';
import { Search, Users, CheckSquare, Square, ChevronDown, ChevronUp } from 'lucide-react';
import type { PatientLite } from '@/services/llmApi';

interface CohortSelectorProps {
  patients: PatientLite[];
  loading: boolean;
  selectedIds: string[];
  onChange: (ids: string[]) => void;
}

export default function CohortSelector({ patients, loading, selectedIds, onChange }: CohortSelectorProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [expanded, setExpanded] = useState(true);

  const filtered = useMemo(() => {
    if (!searchTerm.trim()) return patients;
    const term = searchTerm.toLowerCase();
    return patients.filter(p =>
      p.patientId.toLowerCase().includes(term) ||
      p.displayName.toLowerCase().includes(term)
    );
  }, [patients, searchTerm]);

  const allSelected = filtered.length > 0 && filtered.every(p => selectedIds.includes(p.patientId));
  const someSelected = filtered.some(p => selectedIds.includes(p.patientId));

  const toggleAll = () => {
    if (allSelected) {
      // Deselect all filtered
      onChange(selectedIds.filter(id => !filtered.some(p => p.patientId === id)));
    } else {
      // Select all filtered (merge with existing selection)
      const filteredIds = filtered.map(p => p.patientId);
      onChange([...new Set([...selectedIds, ...filteredIds])]);
    }
  };

  const toggleOne = (patientId: string) => {
    if (selectedIds.includes(patientId)) {
      onChange(selectedIds.filter(id => id !== patientId));
    } else {
      onChange([...selectedIds, patientId]);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 bg-slate-50 border-b border-slate-200 cursor-pointer select-none"
        onClick={() => setExpanded(e => !e)}
      >
        <div className="flex items-center gap-2">
          <Users className="text-sidebar-accent" size={16} />
          <span className="text-sm font-semibold text-slate-800">Select Patient Cohort</span>
          {selectedIds.length > 0 && (
            <span className="bg-sidebar-accent text-white text-xs px-2 py-0.5 rounded-full font-medium">
              {selectedIds.length} selected
            </span>
          )}
        </div>
        {expanded ? <ChevronUp size={16} className="text-slate-400" /> : <ChevronDown size={16} className="text-slate-400" />}
      </div>

      {expanded && (
        <div className="p-3 space-y-3">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-2 top-2.5 text-slate-400" size={13} />
            <input
              type="text"
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              placeholder="Search by name or ID…"
              className="w-full rounded-lg border border-slate-200 bg-slate-50 pl-7 pr-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-sidebar-accent focus:bg-white"
            />
          </div>

          {/* Select All row */}
          {!loading && filtered.length > 0 && (
            <button
              type="button"
              onClick={toggleAll}
              className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs text-slate-600 hover:bg-slate-50 border border-slate-200 transition"
            >
              {allSelected
                ? <CheckSquare size={14} className="text-sidebar-accent flex-shrink-0" />
                : someSelected
                  ? <CheckSquare size={14} className="text-slate-300 flex-shrink-0" />
                  : <Square size={14} className="text-slate-300 flex-shrink-0" />
              }
              <span className="font-medium">
                {allSelected ? 'Deselect all' : `Select all (${filtered.length})`}
              </span>
            </button>
          )}

          {/* Patient list */}
          <div className="max-h-56 overflow-y-auto space-y-1">
            {loading && (
              <div className="space-y-1">
                {[1, 2, 3, 4].map(i => (
                  <div key={i} className="h-9 bg-slate-100 rounded-lg animate-pulse" />
                ))}
              </div>
            )}
            {!loading && filtered.length === 0 && (
              <div className="text-xs text-slate-400 text-center py-4">No patients match your search</div>
            )}
            {!loading && filtered.map(patient => {
              const isSelected = selectedIds.includes(patient.patientId);
              return (
                <button
                  key={patient.patientId}
                  type="button"
                  onClick={() => toggleOne(patient.patientId)}
                  className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs transition border ${
                    isSelected
                      ? 'border-sidebar-accent/50 bg-sidebar-accent/5 text-sidebar-accent'
                      : 'border-slate-200 text-slate-600 hover:border-sidebar-accent/40 hover:bg-slate-50'
                  }`}
                >
                  {isSelected
                    ? <CheckSquare size={14} className="text-sidebar-accent flex-shrink-0" />
                    : <Square size={14} className="text-slate-300 flex-shrink-0" />
                  }
                  <div className="text-left flex-1 min-w-0">
                    <div className="font-medium truncate">{patient.displayName}</div>
                    <div className="text-[10px] text-slate-400">{patient.patientId}</div>
                  </div>
                </button>
              );
            })}
          </div>

          {selectedIds.length > 0 && (
            <button
              type="button"
              onClick={() => onChange([])}
              className="w-full text-xs text-slate-400 hover:text-slate-600 text-center py-1 transition"
            >
              Clear selection
            </button>
          )}
        </div>
      )}
    </div>
  );
}
