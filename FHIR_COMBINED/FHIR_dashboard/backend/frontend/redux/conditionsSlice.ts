import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { fetchDashboardData, fetchAllPatientIds } from '../services/api';

type ConditionPriority = 'high' | 'medium' | 'low';
type ConditionStatus = 'active' | 'inactive' | 'unknown';

interface PatientEntry {
  patient_id: string;
  name: string;
}

interface Condition {
  name: string;
  code: string;
  originalDisplay: string;
  priority: ConditionPriority;
  status: ConditionStatus;
  category: string;
}

interface ConditionCategory {
  category: string;
  conditions: Condition[];
}

interface ConditionStats {
  total: number;
  byCategory: Record<string, number>;
  byPriority: { high: number; medium: number; low: number };
}

interface DashboardData {
  patient_id: string;
  name: string;
  groupedConditions: ConditionCategory[];
  conditionStats: ConditionStats;
  monthly_visits: Record<string, number>;
  avg_length_of_stay: number;
  avg_time_between_visits: number;
  conditions: string[];
  comorbidities: string[];
}

interface StateType {
  patientId: string;
  patientList: PatientEntry[];
  dashboardData: DashboardData | null;
  loading: boolean;
  error: string | null;
}

const PRIORITY_ORDER: Record<ConditionPriority, number> = {
  high: 3,
  medium: 2,
  low: 1
};

const DASHBOARD_CATEGORY_ORDER = [
  'Cardiovascular',
  'Metabolic',
  'Respiratory',
  'Neurological',
  'Mental Health',
  'Musculoskeletal',
  'Gastrointestinal',
  'Renal',
  'Endocrine',
  'Oncology',
  'Infectious',
  'Pregnancy',
  'Therapy',
  'Symptoms',
  'Acute',
  'Other'
] as const;

const CATEGORY_PRECEDENCE = new Map<string, number>(
  DASHBOARD_CATEGORY_ORDER.map((category, index) => [category, index])
);

const CODE_CATEGORY_MAP: Record<
  string,
  { name: string; category: string; priority: ConditionPriority }
> = {
  '307496006': { name: 'Diabetes', category: 'Metabolic', priority: 'high' },
  '44054006': { name: 'Type 2 Diabetes', category: 'Metabolic', priority: 'high' },
  '38341003': { name: 'Hypertension', category: 'Cardiovascular', priority: 'high' },
  '56265001': { name: 'Heart Disease', category: 'Cardiovascular', priority: 'high' },
  '25064002': { name: 'Heart Failure', category: 'Cardiovascular', priority: 'high' },
  '195967001': { name: 'Asthma', category: 'Respiratory', priority: 'high' },
  '13645005': { name: 'COPD', category: 'Respiratory', priority: 'high' },
  '233604007': {
    name: 'Chronic Obstructive Pulmonary Disease',
    category: 'Respiratory',
    priority: 'high'
  },
  '3723001': { name: 'Arthritis', category: 'Musculoskeletal', priority: 'medium' },
  '203082005': { name: 'Fibromyalgia', category: 'Musculoskeletal', priority: 'medium' },
  '64859006': { name: 'Osteoporosis', category: 'Musculoskeletal', priority: 'medium' },
  '35489007': { name: 'Depression', category: 'Mental Health', priority: 'medium' },
  '197480006': { name: 'Anxiety', category: 'Mental Health', priority: 'medium' },
  '55822004': { name: 'Major Depression', category: 'Mental Health', priority: 'high' },
  '26929004': {
    name: "Alzheimer's Disease",
    category: 'Neurological',
    priority: 'high'
  },
  '49049000': {
    name: "Parkinson's Disease",
    category: 'Neurological',
    priority: 'high'
  },
  '24700007': { name: 'Multiple Sclerosis', category: 'Neurological', priority: 'high' },
  '230690007': { name: 'Stroke', category: 'Neurological', priority: 'high' },
  '414916001': { name: 'Obesity', category: 'Metabolic', priority: 'medium' },
  '709044004': { name: 'Chronic Kidney Disease', category: 'Renal', priority: 'high' },
  '363346000': { name: 'Cancer', category: 'Oncology', priority: 'high' }
};

const PATTERN_CATEGORY_MAP: Record<
  string,
  { category: string; priority: ConditionPriority }
> = {
  diabetes: { category: 'Metabolic', priority: 'high' },
  diabetic: { category: 'Metabolic', priority: 'high' },
  dm: { category: 'Metabolic', priority: 'high' },
  'type 2 diabetes': { category: 'Metabolic', priority: 'high' },
  'type 1 diabetes': { category: 'Metabolic', priority: 'high' },
  hypertension: { category: 'Cardiovascular', priority: 'high' },
  htn: { category: 'Cardiovascular', priority: 'high' },
  'high blood pressure': { category: 'Cardiovascular', priority: 'high' },
  cardiac: { category: 'Cardiovascular', priority: 'high' },
  'heart failure': { category: 'Cardiovascular', priority: 'high' },
  'heart disease': { category: 'Cardiovascular', priority: 'high' },
  heart: { category: 'Cardiovascular', priority: 'high' },
  copd: { category: 'Respiratory', priority: 'high' },
  asthma: { category: 'Respiratory', priority: 'high' },
  pneumonia: { category: 'Respiratory', priority: 'high' },
  bronchitis: { category: 'Respiratory', priority: 'medium' },
  depression: { category: 'Mental Health', priority: 'medium' },
  anxiety: { category: 'Mental Health', priority: 'medium' },
  ptsd: { category: 'Mental Health', priority: 'high' },
  bipolar: { category: 'Mental Health', priority: 'high' },
  stroke: { category: 'Neurological', priority: 'high' },
  epilepsy: { category: 'Neurological', priority: 'high' },
  seizure: { category: 'Neurological', priority: 'high' },
  dementia: { category: 'Neurological', priority: 'high' },
  alzheimer: { category: 'Neurological', priority: 'high' },
  parkinson: { category: 'Neurological', priority: 'high' },
  arthritis: { category: 'Musculoskeletal', priority: 'medium' },
  osteoarthritis: { category: 'Musculoskeletal', priority: 'medium' },
  rheumatoid: { category: 'Musculoskeletal', priority: 'high' },
  fibromyalgia: { category: 'Musculoskeletal', priority: 'medium' },
  osteoporosis: { category: 'Musculoskeletal', priority: 'medium' },
  crohn: { category: 'Gastrointestinal', priority: 'high' },
  colitis: { category: 'Gastrointestinal', priority: 'high' },
  ibd: { category: 'Gastrointestinal', priority: 'high' },
  ibs: { category: 'Gastrointestinal', priority: 'medium' },
  gastroenteritis: { category: 'Gastrointestinal', priority: 'medium' },
  kidney: { category: 'Renal', priority: 'high' },
  renal: { category: 'Renal', priority: 'high' },
  ckd: { category: 'Renal', priority: 'high' },
  nephropathy: { category: 'Renal', priority: 'high' },
  obesity: { category: 'Metabolic', priority: 'medium' },
  obese: { category: 'Metabolic', priority: 'medium' },
  thyroid: { category: 'Endocrine', priority: 'medium' },
  hypothyroid: { category: 'Endocrine', priority: 'medium' },
  hyperthyroid: { category: 'Endocrine', priority: 'medium' },
  cancer: { category: 'Oncology', priority: 'high' },
  tumor: { category: 'Oncology', priority: 'high' },
  malignancy: { category: 'Oncology', priority: 'high' },
  neoplasm: { category: 'Oncology', priority: 'high' },
  e86: { category: 'Metabolic', priority: 'medium' },
  e87: { category: 'Metabolic', priority: 'medium' },
  g43: { category: 'Neurological', priority: 'medium' },
  k52: { category: 'Gastrointestinal', priority: 'medium' },
  i10: { category: 'Cardiovascular', priority: 'high' },
  e11: { category: 'Metabolic', priority: 'high' },
  j44: { category: 'Respiratory', priority: 'high' },
  j45: { category: 'Respiratory', priority: 'high' }
};

const KEYWORD_CATEGORY_MAP: Array<{
  test: RegExp;
  category: string;
  priority: ConditionPriority;
}> = [
  { test: /(hypertension|blood pressure|cardio|heart|atrial|cardiac|ischemic|vascular)/i, category: 'Cardiovascular', priority: 'high' },
  { test: /(copd|asthma|bronch|pulmon|respiratory|sleep apnea|oxygen|lung|sob)/i, category: 'Respiratory', priority: 'high' },
  { test: /(depress|anxiet|bipolar|ptsd|panic|mood|psych|mental|autism|adhd|stress)/i, category: 'Mental Health', priority: 'medium' },
  { test: /(stroke|seizure|migraine|dementia|parkinson|neuropathy|cva|tbi|neur|brain)/i, category: 'Neurological', priority: 'high' },
  { test: /(arthritis|spondyl|sciatica|fracture|osteoporosis|muscle|joint|back pain|hip|knee|shoulder|spine|tendon|ligament)/i, category: 'Musculoskeletal', priority: 'medium' },
  { test: /(crohn|colit|reflux|gerd|gastro|abdominal|abdomen|nausea|vomit|bowel|constipation|liver|hepat|pancre|colon)/i, category: 'Gastrointestinal', priority: 'medium' },
  { test: /(kidney|renal|nephro|dialysis|uti|bladder|urinary)/i, category: 'Renal', priority: 'high' },
  { test: /(thyroid|diabet|obesity|weight|metabolic|lipid|cholesterol|endocrine)/i, category: 'Metabolic', priority: 'medium' },
  { test: /(cancer|tumor|malignan|carcinoma|lymphoma|leukemia|oncolog)/i, category: 'Oncology', priority: 'high' },
  { test: /(infection|sepsis|cellulitis|viral|bacterial|abscess|pneumonia|hepatitis)/i, category: 'Infectious', priority: 'medium' },
  { test: /(pregnan|gestation|prenatal|postpartum|obstetric)/i, category: 'Pregnancy', priority: 'medium' },
  { test: /(injury|trauma|wound|laceration|burn|amputation|fracture)/i, category: 'Acute', priority: 'medium' },
  { test: /(pain|fatigue|weakness|dizziness|syncope|fall|gait)/i, category: 'Symptoms', priority: 'low' }
];

const toTitleCase = (value: string): string => {
  if (!value) return value;
  return value
    .toLowerCase()
    .replace(/\b([a-z])/g, (match) => match.toUpperCase());
};

const asPriority = (value: unknown): ConditionPriority => {
  if (value === 'high' || value === 'medium' || value === 'low') return value;
  return 'low';
};

const asStatus = (value: unknown): ConditionStatus => {
  if (value === 'active' || value === 'inactive' || value === 'unknown') return value;
  return 'unknown';
};

const toNumber = (value: unknown): number => {
  const num = Number(value);
  return Number.isFinite(num) ? num : 0;
};

const cleanCode = (value?: string): string => {
  if (!value) return '';
  return value.split('^')[0]?.trim() ?? '';
};

const cleanDisplay = (value?: string): string => {
  if (!value) return '';
  const parts = value.split('^');
  if (parts.length > 1) {
    return parts[1]?.trim() || parts[0]?.trim() || '';
  }
  return value.trim();
};

const parseConditionString = (raw: string): { code: string; display: string } => {
  const trimmed = raw.trim();
  if (!trimmed) return { code: '', display: '' };

  if (trimmed.includes('^')) {
    return {
      code: cleanCode(trimmed),
      display: cleanDisplay(trimmed)
    };
  }

  const match = trimmed.match(/^([A-Z0-9.\-+]+)\s+(.*)$/i);
  if (match) {
    return { code: match[1].trim(), display: match[2].trim() };
  }

  return { code: '', display: trimmed };
};

const categorizeCondition = (
  codeInput?: string,
  displayInput?: string,
  statusInput?: ConditionStatus,
  fallbackName?: string
): Condition => {
  const cleanCodeValue = cleanCode(codeInput);
  const cleanDisplayValue = cleanDisplay(displayInput);
  const status = statusInput ?? 'unknown';

  let name = (fallbackName ?? cleanDisplayValue ?? cleanCodeValue ?? '').trim();
  if (!name) name = 'Unknown Condition';

  let category = 'Other';
  let priority: ConditionPriority = 'low';

  const codeKey = cleanCodeValue.toUpperCase();
  if (CODE_CATEGORY_MAP[codeKey]) {
    const info = CODE_CATEGORY_MAP[codeKey];
    name = info.name;
    category = info.category;
    priority = info.priority;
  } else if (/^[A-Z]\d{2}/i.test(codeKey)) {
    const icdPrefix = codeKey.slice(0, 3).toLowerCase();
    if (PATTERN_CATEGORY_MAP[icdPrefix]) {
      const info = PATTERN_CATEGORY_MAP[icdPrefix];
      category = info.category;
      priority = info.priority;
    }
  }

  if (category === 'Other') {
    const searchText = `${cleanCodeValue} ${cleanDisplayValue} ${name}`.toLowerCase();
    for (const [pattern, info] of Object.entries(PATTERN_CATEGORY_MAP)) {
      if (searchText.includes(pattern)) {
        category = info.category;
        priority = info.priority;
        break;
      }
    }
  }

  if (category === 'Other') {
    const keywordTarget = `${cleanCodeValue} ${cleanDisplayValue} ${name}`;
    for (const matcher of KEYWORD_CATEGORY_MAP) {
      if (matcher.test.test(keywordTarget)) {
        category = matcher.category;
        priority = matcher.priority;
        break;
      }
    }
  }

  const originalDisplay = cleanDisplayValue || name;

  return {
    name: toTitleCase(name),
    code: cleanCodeValue,
    originalDisplay,
    priority,
    status,
    category
  };
};

const dedupeConditions = (conditions: Condition[]): Condition[] => {
  const seen = new Map<string, Condition>();
  for (const condition of conditions) {
    const key = `${condition.category}|${condition.name}|${condition.code}`;
    if (seen.has(key)) continue;
    seen.set(key, condition);
  }
  return Array.from(seen.values());
};

const conditionSortFn = (a: Condition, b: Condition): number => {
  const priorityDelta = PRIORITY_ORDER[b.priority] - PRIORITY_ORDER[a.priority];
  if (priorityDelta !== 0) return priorityDelta;
  return a.name.localeCompare(b.name);
};

const normalizeCondition = (raw: any): Condition => {
  if (
    raw &&
    typeof raw === 'object' &&
    typeof raw.name === 'string' &&
    typeof raw.category === 'string' &&
    typeof raw.priority === 'string'
  ) {
    return {
      name: raw.name.trim() || 'Unknown Condition',
      code: cleanCode(raw.code ?? ''),
      originalDisplay:
        typeof raw.originalDisplay === 'string'
          ? raw.originalDisplay
          : cleanDisplay(raw.display ?? raw.name),
      priority: asPriority(raw.priority),
      status: asStatus(raw.status ?? raw.clinical_status),
      category: raw.category.trim() || 'Other'
    };
  }

  if (raw && typeof raw === 'object') {
    const code = cleanCode(raw.code ?? '');
    const display =
      cleanDisplay(raw.display ?? raw.originalDisplay ?? raw.name ?? '') ||
      cleanDisplay(raw.description ?? '');
    const status = asStatus(raw.status ?? raw.clinical_status);
    const name =
      typeof raw.name === 'string' && raw.name.trim()
        ? raw.name
        : typeof display === 'string' && display.trim()
          ? display
          : undefined;
    return categorizeCondition(code, display, status, name);
  }

  if (typeof raw === 'string') {
    const parsed = parseConditionString(raw);
    return categorizeCondition(parsed.code, parsed.display, 'unknown', parsed.display);
  }

  return categorizeCondition('', '', 'unknown');
};

const ESSENTIAL_CATEGORIES = new Set<string>([
  'Cardiovascular',
  'Metabolic',
  'Respiratory',
  'Neurological',
  'Mental Health',
  'Musculoskeletal',
  'Gastrointestinal',
  'Renal',
  'Endocrine',
  'Oncology'
]);

const MAX_CONDITIONS_PER_CATEGORY = 12;

const filterRelevantConditions = (conditions: Condition[]): Condition[] => {
  return dedupeConditions(conditions)
    .filter((condition) => {
      if (condition.priority === 'high') return true;
      if (condition.priority === 'medium' && ESSENTIAL_CATEGORIES.has(condition.category)) return true;
      return false;
    })
    .slice(0, MAX_CONDITIONS_PER_CATEGORY);
};

const normalizeGroupedConditions = (raw: any): ConditionCategory[] => {
  if (!Array.isArray(raw)) return [];

  return raw
    .map((group) => {
      const category =
        typeof group?.category === 'string' && group.category.trim()
          ? group.category
          : 'Other';
      const conditions = Array.isArray(group?.conditions)
        ? filterRelevantConditions(group.conditions.map(normalizeCondition).filter(Boolean).sort(conditionSortFn))
        : [];
      return { category, conditions };
    })
    .filter((group) => group.conditions.length > 0);
};

const deriveStatsFromGroups = (groups: ConditionCategory[]): ConditionStats => {
  const stats: ConditionStats = {
    total: 0,
    byCategory: {},
    byPriority: { high: 0, medium: 0, low: 0 }
  };

  for (const group of groups) {
    stats.byCategory[group.category] =
      (stats.byCategory[group.category] || 0) + group.conditions.length;
    stats.total += group.conditions.length;
    for (const condition of group.conditions) {
      stats.byPriority[condition.priority] += 1;
    }
  }

  return stats;
};

const normalizeStats = (raw: any, groups: ConditionCategory[]): ConditionStats => {
  if (raw && typeof raw === 'object') {
    const stats: ConditionStats = {
      total: toNumber(raw.total),
      byCategory: {},
      byPriority: { high: 0, medium: 0, low: 0 }
    };

    if (raw.byCategory && typeof raw.byCategory === 'object') {
      for (const [key, value] of Object.entries(raw.byCategory)) {
        stats.byCategory[key] = toNumber(value);
      }
    }

    if (raw.byPriority && typeof raw.byPriority === 'object') {
      stats.byPriority.high = toNumber(raw.byPriority.high);
      stats.byPriority.medium = toNumber(raw.byPriority.medium);
      stats.byPriority.low = toNumber(raw.byPriority.low);
    }

    if (stats.total === 0 && Object.keys(stats.byCategory).length === 0) {
      return deriveStatsFromGroups(groups);
    }

    return stats;
  }

  return deriveStatsFromGroups(groups);
};

const normalizeDashboardData = (raw: any): DashboardData => {
  const grouped =
    normalizeGroupedConditions(raw?.groupedConditions ?? raw?.grouped_conditions ?? []);

  const rawConditions = Array.isArray(raw?.conditions) ? raw.conditions : [];
  const rawComorbidities = Array.isArray(raw?.comorbidities) ? raw.comorbidities : [];

  let groupedConditions = grouped;

  if (groupedConditions.length === 0) {
    const allConditions = dedupeConditions(
      [...rawConditions, ...rawComorbidities].map(normalizeCondition)
    );

    if (allConditions.length) {
      const byCategory: Record<string, Condition[]> = {};
      allConditions.forEach((condition) => {
        if (!byCategory[condition.category]) byCategory[condition.category] = [];
        byCategory[condition.category].push(condition);
      });

      groupedConditions = Object.entries(byCategory)
        .map(([category, conditions]) => ({
          category,
          conditions: filterRelevantConditions(conditions.sort(conditionSortFn))
        }))
        .sort((a, b) => {
          const aRank = CATEGORY_PRECEDENCE.has(a.category)
            ? CATEGORY_PRECEDENCE.get(a.category)!
            : Number.MAX_SAFE_INTEGER;
          const bRank = CATEGORY_PRECEDENCE.has(b.category)
            ? CATEGORY_PRECEDENCE.get(b.category)!
            : Number.MAX_SAFE_INTEGER;
          if (aRank !== bRank) return aRank - bRank;
          return b.conditions.length - a.conditions.length;
        });
    }
  } else {
    groupedConditions = groupedConditions
      .map((group) => ({
        category: group.category,
        conditions: filterRelevantConditions(group.conditions.sort(conditionSortFn))
      }))
      .sort((a, b) => {
        const aRank = CATEGORY_PRECEDENCE.has(a.category)
          ? CATEGORY_PRECEDENCE.get(a.category)!
          : Number.MAX_SAFE_INTEGER;
        const bRank = CATEGORY_PRECEDENCE.has(b.category)
          ? CATEGORY_PRECEDENCE.get(b.category)!
          : Number.MAX_SAFE_INTEGER;
        if (aRank !== bRank) return aRank - bRank;
        return b.conditions.length - a.conditions.length;
      });
  }

  const conditionStats = normalizeStats(
    raw?.conditionStats ?? raw?.condition_stats ?? null,
    groupedConditions
  );

  const monthlyVisits: Record<string, number> = {};
  if (raw?.monthly_visits && typeof raw.monthly_visits === 'object') {
    for (const [key, value] of Object.entries(raw.monthly_visits)) {
      monthlyVisits[key] = toNumber(value);
    }
  }

  return {
    patient_id: typeof raw?.patient_id === 'string' ? raw.patient_id : '',
    name: typeof raw?.name === 'string' ? raw.name : 'Unknown Patient',
    groupedConditions,
    conditionStats,
    monthly_visits: monthlyVisits,
    avg_length_of_stay: toNumber(raw?.avg_length_of_stay),
    avg_time_between_visits: toNumber(raw?.avg_time_between_visits),
    conditions: groupedConditions.flatMap((group) => group.conditions.map((c) => c.name)),
    comorbidities: rawComorbidities
  };
};

export const getDashboardData = createAsyncThunk(
  'conditions/getDashboardData',
  async (patientId: string) => {
    const res = await fetchDashboardData(patientId);
    return normalizeDashboardData(res);
  }
);

export const getAllPatients = createAsyncThunk(
  'conditions/getAllPatients',
  async () => {
    const res = await fetchAllPatientIds();
    const sorted = [...res].sort((a: PatientEntry, b: PatientEntry) => {
      const aVal = parseInt(a.patient_id, 10);
      const bVal = parseInt(b.patient_id, 10);

      if (!Number.isNaN(aVal) && !Number.isNaN(bVal)) {
        return aVal - bVal;
      }

      return a.patient_id.localeCompare(b.patient_id, undefined, {
        numeric: true,
        sensitivity: 'base',
      });
    });
    return sorted;
  }
);

const initialState: StateType = {
  patientId: '',
  patientList: [],
  dashboardData: null,
  loading: false,
  error: null
};

const conditionsSlice = createSlice({
  name: 'conditions',
  initialState,
  reducers: {
    setPatientId: (state, action: PayloadAction<string>) => {
      state.patientId = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(getDashboardData.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(getDashboardData.fulfilled, (state, action) => {
        state.loading = false;
        state.dashboardData = action.payload;
      })
      .addCase(getDashboardData.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to load dashboard data';
        state.dashboardData = null;
      })

      .addCase(getAllPatients.pending, (state) => {
        state.error = null;
      })
      .addCase(getAllPatients.fulfilled, (state, action) => {
        state.patientList = action.payload;
      })
      .addCase(getAllPatients.rejected, (state, action) => {
        state.error = action.error.message || 'Failed to load patient list';
        state.patientList = [];
      });
  }
});

export const { setPatientId } = conditionsSlice.actions;
export default conditionsSlice.reducer;
