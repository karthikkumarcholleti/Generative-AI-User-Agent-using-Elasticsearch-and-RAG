"use client"

import React from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { SourceDetail } from '@/services/llmApi';
import { Search, Calendar, Hash, BarChart3, FileText, Activity } from 'lucide-react';

interface SourceDetailModalProps {
  source: SourceDetail | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function SourceDetailModal({ source, open, onOpenChange }: SourceDetailModalProps) {
  if (!source) return null;

  const formatDate = (dateStr: string) => {
    if (!dateStr) return 'N/A';
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  const formatScore = (score: number) => {
    // Elasticsearch scores are already in their raw format (0-100+)
    // Don't multiply by 100 - just format with 2 decimal places
    return score.toFixed(2);
  };

  const getDataTypeIcon = (dataType: string) => {
    switch (dataType.toLowerCase()) {
      case 'observations':
        return <Activity className="h-4 w-4" />;
      case 'conditions':
        return <BarChart3 className="h-4 w-4" />;
      case 'notes':
        return <FileText className="h-4 w-4" />;
      default:
        return <Search className="h-4 w-4" />;
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {getDataTypeIcon(source.data_type)}
            <span className="capitalize">{source.data_type} Source Details</span>
          </DialogTitle>
          <DialogDescription>
            Detailed information about this data source. Use this to verify the LLM's response.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 mt-4">
          {/* Description */}
          <div className="bg-slate-50 rounded-lg p-3 border border-slate-200">
            <div className="text-sm font-semibold text-slate-600 mb-1">Summary</div>
            <div className="text-sm text-slate-700">{source.description}</div>
          </div>

          {/* Key Information Grid */}
          <div className="grid grid-cols-2 gap-4">
            {/* Display Name */}
            {source.display && (
              <div className="space-y-1">
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                  Display Name
                </div>
                <div className="text-sm text-slate-800">{source.display}</div>
              </div>
            )}

            {/* Value */}
            {source.value && (
              <div className="space-y-1">
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                  Value
                </div>
                <div className="text-sm text-slate-800 font-medium">
                  {source.value} {source.unit ? source.unit : ''}
                </div>
              </div>
            )}

            {/* Code */}
            {source.code && (
              <div className="space-y-1">
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide flex items-center gap-1">
                  <Hash className="h-3 w-3" />
                  Code
                </div>
                <div className="text-sm text-slate-800 font-mono">{source.code}</div>
              </div>
            )}

            {/* Date */}
            {source.date && (
              <div className="space-y-1">
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide flex items-center gap-1">
                  <Calendar className="h-3 w-3" />
                  Date
                </div>
                <div className="text-sm text-slate-800">{formatDate(source.date)}</div>
              </div>
            )}

            {/* Relevance Score */}
            <div className="space-y-1">
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                Relevance Score
              </div>
              <div className="text-sm text-slate-800">
                {formatScore(source.score)} (relevance score)
              </div>
            </div>

            {/* Filename (for notes) */}
            {source.filename && (
              <div className="space-y-1">
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                  File Name
                </div>
                <div className="text-sm text-slate-800 font-mono text-xs truncate">
                  {source.filename}
                </div>
              </div>
            )}
          </div>

          {/* Full Content */}
          {source.content && (
            <div className="space-y-2">
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                Full Content
              </div>
              <div className="bg-slate-50 rounded-lg p-3 border border-slate-200 max-h-64 overflow-y-auto">
                <pre className="text-xs text-slate-700 whitespace-pre-wrap font-sans">
                  {source.content}
                </pre>
              </div>
            </div>
          )}

          {/* Metadata (if available) */}
          {source.metadata && Object.keys(source.metadata).length > 0 && (
            <div className="space-y-2">
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                Additional Metadata
              </div>
              <div className="bg-slate-50 rounded-lg p-3 border border-slate-200">
                <pre className="text-xs text-slate-700 whitespace-pre-wrap font-mono overflow-x-auto">
                  {JSON.stringify(source.metadata, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {/* Source ID (for debugging) */}
          <div className="pt-3 border-t border-slate-200">
            <div className="text-xs text-slate-400 font-mono">
              Source ID: {source.source_id}
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

