// components/ConditionsAndComorbiditiesTable.tsx
import React from 'react';
import { motion } from 'framer-motion';

interface Condition {
  name: string;
  code: string;
  originalDisplay: string;
  priority: 'high' | 'medium' | 'low';
  status: 'active' | 'inactive' | 'unknown';
  category: string;
}

type ConditionLike = Condition | string;

interface ConditionCategory {
  category?: string;
  condition?: string;
  conditions?: ConditionLike[];
  comorbidities?: ConditionLike[];
}

interface ConditionStats {
  total: number;
  byCategory: Record<string, number>;
  byPriority: { high: number; medium: number; low: number };
}

interface Props {
  groupedConditions: ConditionCategory[];
  conditionStats?: ConditionStats;
}

type ConditionPriority = 'high' | 'medium' | 'low';

const defaultCondition: Condition = {
  name: 'Unknown',
  code: '',
  originalDisplay: 'Unknown',
  priority: 'medium',
  status: 'unknown',
  category: 'General'
};

function toCondition(item: ConditionLike, fallbackCategory: string): Condition {
  if (typeof item === 'string') {
    return {
      ...defaultCondition,
      name: item,
      originalDisplay: item,
      category: fallbackCategory,
    };
  }

  return {
    ...defaultCondition,
    ...item,
    category: item.category || fallbackCategory,
    name: item.name || item.originalDisplay || item.code || 'Unknown',
    originalDisplay: item.originalDisplay || item.name || item.code || 'Unknown',
    priority: (item.priority ?? 'medium') as ConditionPriority,
    status: item.status ?? 'unknown',
  };
}

const ConditionsAndComorbiditiesTable: React.FC<Props> = ({
  groupedConditions,
  conditionStats,
}) => {
  if (process.env.NODE_ENV !== 'production') {
    console.log('ConditionsAndComorbiditiesTable data', {
      categories: groupedConditions?.length ?? 0,
      conditionCount: groupedConditions?.reduce((acc, group) => acc + group.conditions.length, 0) ?? 0,
      conditionStats
    });
  }

  // Helper function to get priority color
  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'bg-red-100 text-red-800 border-red-200';
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low': return 'bg-green-100 text-green-800 border-green-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'inactive':
        return 'bg-gray-100 text-gray-600 border-gray-200';
      case 'unknown':
        return 'bg-yellow-100 text-yellow-700 border-yellow-200';
      default:
        return 'bg-gray-100 text-gray-600 border-gray-200';
    }
  };

  // Helper function to get category color
  const getCategoryColor = (category: string) => {
    const colors = {
      'Cardiovascular': 'bg-red-50 border-red-200',
      'Respiratory': 'bg-blue-50 border-blue-200',
      'Mental Health': 'bg-purple-50 border-purple-200',
      'Neurological': 'bg-indigo-50 border-indigo-200',
      'Musculoskeletal': 'bg-orange-50 border-orange-200',
      'Gastrointestinal': 'bg-green-50 border-green-200',
      'Renal': 'bg-cyan-50 border-cyan-200',
      'Endocrine': 'bg-pink-50 border-pink-200',
      'Acute': 'bg-yellow-50 border-yellow-200',
      'Other': 'bg-gray-50 border-gray-200'
    };
    return colors[category as keyof typeof colors] || 'bg-gray-50 border-gray-200';
  };

  const preparedGroups = groupedConditions
    .map((categoryGroup) => {
      const categoryLabel =
        categoryGroup.category ?? categoryGroup.condition ?? 'General';
      const rawConditions =
        categoryGroup.conditions ?? categoryGroup.comorbidities ?? [];
      const normalizedConditions = rawConditions.map((condition) =>
        toCondition(condition, categoryLabel)
      );

      return {
        categoryLabel,
        normalizedConditions,
      };
    })
    .filter((group) => group.normalizedConditions.length > 0);

  return (
    <motion.div
      whileHover={{ y: -2, scale: 1.01 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className="group relative bg-gradient-to-br from-white via-slate-50/30 to-slate-100/20 rounded-2xl shadow-lg border-2 border-slate-300/60 hover:shadow-2xl hover:border-sidebar-accent/60 transition-all duration-500 overflow-hidden"
    >
      {/* Animated Accent Strip */}
      <motion.div 
        initial={{ x: '-100%' }}
        animate={{ x: '100%' }}
        transition={{ 
          duration: 3, 
          ease: "easeInOut", 
          repeat: Infinity, 
          repeatDelay: 4 
        }}
        className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-sidebar-accent to-sidebar-accent-hover"
      />
      
      {/* Hover Glow Effect */}
      <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-sidebar-accent/5 to-sidebar-accent-hover/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
      
      {/* Header */}
      <div className="relative z-10 bg-gradient-to-r from-sidebar-accent to-sidebar-accent-hover text-white px-6 py-4 rounded-t-2xl">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 bg-white rounded-full"></div>
            <h3 className="text-lg font-semibold">Medical Conditions & Comorbidities</h3>
          </div>
          {conditionStats && (
            <div className="text-sm text-white/90">
              <span className="font-semibold">{conditionStats.total}</span> total conditions
              <span className="mx-2">•</span>
              <span className="font-semibold">{preparedGroups.length}</span> categories
            </div>
          )}
        </div>
      </div>
      
      {/* Content */}
      <div className="relative z-10 p-6">
        {preparedGroups.length ? (
          <div className="space-y-6">
            {preparedGroups.map((group, idx) => (
              <motion.div
                key={`${group.categoryLabel}-${idx}`}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.1, duration: 0.4 }}
                className={`rounded-xl border-2 p-4 ${getCategoryColor(group.categoryLabel)}`}
              >
                {/* Category Header */}
                <div className="flex items-center justify-between mb-4">
                  <h4 className="text-lg font-semibold text-slate-800 capitalize">
                    {group.categoryLabel}
                  </h4>
                  <span className="text-sm text-slate-600 bg-white/50 px-3 py-1 rounded-full">
                    {group.normalizedConditions.length} condition
                    {group.normalizedConditions.length !== 1 ? 's' : ''}
                  </span>
                </div>

                {/* Conditions Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {group.normalizedConditions.map((condition, conditionIdx) => (
                    <motion.div
                      key={`${condition.code}-${conditionIdx}`}
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{
                        delay: idx * 0.1 + conditionIdx * 0.05,
                        duration: 0.3,
                      }}
                      className="bg-white/70 rounded-lg p-3 border border-white/50 hover:bg-white/90 transition-all duration-200"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <h5 className="font-medium text-slate-800 text-sm leading-tight">
                          {condition.name}
                        </h5>
                        <div className="flex gap-1">
                          <span
                            className={`px-2 py-1 text-xs rounded-full border ${getPriorityColor(condition.priority)}`}
                          >
                            {condition.priority}
                          </span>
                          <span
                            className={`px-2 py-1 text-xs rounded-full border ${getStatusColor(condition.status)}`}
                          >
                            {condition.status}
                          </span>
                        </div>
                      </div>

                      {condition.originalDisplay && condition.originalDisplay !== condition.name && (
                        <p className="text-xs text-slate-500 mb-2 italic">
                          Original: {condition.originalDisplay}
                        </p>
                      )}

                      {condition.code && (
                        <p className="text-xs text-slate-400 font-mono">
                          Code: {condition.code}
                        </p>
                      )}
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            ))}
          </div>
        ) : (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.3 }}
            className="text-center text-slate-500 py-12"
          >
            <div className="w-20 h-20 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-10 h-10 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-slate-700 mb-2">No Medical Conditions Found</h3>
            <p className="text-slate-500">No conditions have been recorded for this patient.</p>
          </motion.div>
        )}
      </div>
      
      {/* Decorative Background Elements */}
      <div className="absolute top-4 right-4 opacity-5 group-hover:opacity-10 transition-opacity duration-500">
        <div className="w-16 h-16 bg-sidebar-accent rounded-full"></div>
      </div>
      <div className="absolute bottom-4 right-8 opacity-5 group-hover:opacity-10 transition-opacity duration-500">
        <div className="w-8 h-8 bg-sidebar-accent rounded-full"></div>
      </div>
    </motion.div>
  );
};

export default ConditionsAndComorbiditiesTable;
