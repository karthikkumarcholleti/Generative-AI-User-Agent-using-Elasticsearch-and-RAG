// components/PatientSearch.tsx
import React, { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { Search, X, User } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';

interface Patient {
  patient_id: string;
  name: string;
  metadata?: {
    age?: number;
    gender?: string;
    city?: string;
    state?: string;
  };
}

interface PatientSearchProps {
  value?: string;
  onChange: (patientId: string, patient?: Patient) => void;
  placeholder?: string;
  className?: string;
}

export default function PatientSearch({
  value,
  onChange,
  placeholder = 'Search patients by name or ID...',
  className = ''
}: PatientSearchProps) {
  const [query, setQuery] = useState('');
  const [patients, setPatients] = useState<Patient[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const searchRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0, width: 0 });

  // Load default patient list on mount
  useEffect(() => {
    const loadDefaultPatients = async () => {
      try {
        const response = await axios.get('http://localhost:5000/api/patients', {
          params: { limit: 10 }
        });
        if (response.data && response.data.length > 0) {
          setPatients(response.data);
        }
      } catch (error) {
        console.error('Error loading default patients:', error);
      }
    };
    loadDefaultPatients();
  }, []);

  // Show dropdown when default patients load and query is empty
  useEffect(() => {
    if (!query.trim() && patients.length > 0) {
      setIsOpen(true);
    }
  }, [patients, query]);

  // Debounce search
  useEffect(() => {
    if (!query.trim()) {
      return;
    }

    const timeoutId = setTimeout(() => {
      searchPatients(query);
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [query]);

  // Update dropdown position when input position changes
  useEffect(() => {
    const updatePosition = () => {
      if (inputRef.current) {
        const rect = inputRef.current.getBoundingClientRect();
        // Use viewport coordinates since dropdown is rendered via portal to document.body
        setDropdownPosition({
          top: rect.bottom + 4, // 4px gap, no need for scrollY since getBoundingClientRect is viewport-relative
          left: rect.left, // No need for scrollX since getBoundingClientRect is viewport-relative
          width: rect.width
        });
      }
    };

    if (isOpen) {
      updatePosition();
      // Listen to scroll on all scrollable containers (including the page itself)
      window.addEventListener('scroll', updatePosition, true);
      window.addEventListener('resize', updatePosition);
      // Also listen to scroll on the document body and any parent containers
      document.addEventListener('scroll', updatePosition, true);
    }

    return () => {
      window.removeEventListener('scroll', updatePosition, true);
      window.removeEventListener('resize', updatePosition);
      document.removeEventListener('scroll', updatePosition, true);
    };
  }, [isOpen]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        // Check if click is on the portal dropdown
        const target = event.target as HTMLElement;
        if (!target.closest('.patient-search-dropdown-portal')) {
          setIsOpen(false);
        }
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  const searchPatients = async (searchQuery: string) => {
    setIsLoading(true);
    try {
      // Use database-based search endpoint (not Elasticsearch)
      const response = await axios.get('http://localhost:5000/api/patients', {
        params: { q: searchQuery, limit: 10 }
      });
      setPatients(response.data);
      setIsOpen(response.data.length > 0);
    } catch (error) {
      console.error('Error searching patients:', error);
      setPatients([]);
      setIsOpen(false);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelect = (patient: Patient) => {
    setSelectedPatient(patient);
    setQuery(patient.name || `Patient ${patient.patient_id}`);
    setIsOpen(false);
    onChange(patient.patient_id, patient);
  };

  const handleClear = () => {
    setQuery('');
    setSelectedPatient(null);
    setPatients([]);
    setIsOpen(false);
    onChange('');
  };

  const displayText = selectedPatient
    ? selectedPatient.name || `Patient ${selectedPatient.patient_id}`
    : query;

  return (
    <div ref={searchRef} className={`relative ${className}`}>
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <Search className="h-5 w-5 text-slate-400" />
        </div>
        <input
          ref={inputRef}
          type="text"
          value={displayText}
          onChange={(e) => {
            setQuery(e.target.value);
            setSelectedPatient(null);
            onChange('');
          }}
          onFocus={() => {
            // Always show dropdown when focused, load default list if needed
            if (patients.length > 0) {
              setIsOpen(true);
            } else {
              // Load default list if not already loaded
              const loadDefault = async () => {
                try {
                  const response = await axios.get('http://localhost:5000/api/patients', {
                    params: { limit: 10 }
                  });
                  if (response.data && response.data.length > 0) {
                    setPatients(response.data);
                    setIsOpen(true);
                  }
                } catch (error) {
                  console.error('Error loading default patients:', error);
                }
              };
              loadDefault();
            }
          }}
          placeholder={placeholder}
          className="w-full pl-10 pr-10 py-2.5 border border-slate-200 rounded-lg text-sm bg-white shadow-sm focus:ring-2 focus:ring-sidebar-accent focus:border-sidebar-accent transition-all duration-200"
        />
        {query && (
          <button
            onClick={handleClear}
            className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Render dropdown using Portal to bypass stacking contexts */}
      {typeof window !== 'undefined' && createPortal(
        <AnimatePresence>
          {isOpen && (patients.length > 0 || isLoading) && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
              className="patient-search-dropdown-portal fixed z-[99999] bg-white border border-slate-200 rounded-lg shadow-xl max-h-60 overflow-auto"
              style={{
                top: `${dropdownPosition.top}px`,
                left: `${dropdownPosition.left}px`,
                width: `${dropdownPosition.width}px`
              }}
            >
              {isLoading ? (
                <div className="p-4 text-center text-slate-500 text-sm">
                  Searching...
                </div>
              ) : patients.length === 0 ? (
                <div className="p-4 text-center text-slate-500 text-sm">
                  No patients found
                </div>
              ) : (
                <ul className="py-1">
                  {patients.map((patient) => (
                    <li key={patient.patient_id}>
                      <button
                        onClick={() => handleSelect(patient)}
                        className="w-full px-4 py-2 text-left hover:bg-slate-50 focus:bg-slate-50 focus:outline-none transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-sidebar-accent/10 flex items-center justify-center">
                            <User className="h-4 w-4 text-sidebar-accent" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="text-sm font-medium text-slate-900 truncate">
                              {patient.name || `Patient ${patient.patient_id}`}
                            </div>
                            <div className="text-xs text-slate-500">
                              ID: {patient.patient_id}
                              {patient.metadata?.age && ` • Age: ${patient.metadata.age}`}
                              {patient.metadata?.gender && ` • ${patient.metadata.gender}`}
                              {patient.metadata?.city && ` • ${patient.metadata.city}, ${patient.metadata.state || ''}`}
                            </div>
                          </div>
                        </div>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </motion.div>
          )}
        </AnimatePresence>,
        document.body
      )}
    </div>
  );
}

