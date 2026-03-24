import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import api from '@/services/api';

interface SummaryStats {
  patients: number;
  observations: number;
  conditions: number;
  encounters: number;
}

interface GenderStat {
  gender: string;
  count: number;
}

interface ChronicCondition {
  condition: string;
  count: number;
}

interface AdmissionStat {
  reason: string;
  count: number;
}

interface StatsState {
  averageAge: number | null;
  loading: boolean;
  error: string | null;
  summary: SummaryStats | null;
  genderStats: GenderStat[];
  chronicConditions: ChronicCondition[];
  admissions: AdmissionStat[];
}

const initialState: StatsState = {
  averageAge: null,
  loading: false,
  error: null,
  summary: null,
  genderStats: [],
  chronicConditions: [],
  admissions: [],
};

// Thunks
export const fetchAverageAge = createAsyncThunk('stats/fetchAverageAge', async () => {
  const res = await api.get('/stats/age');
  return res.data;
});

export const fetchSummaryStats = createAsyncThunk('stats/fetchSummaryStats', async () => {
  const res = await api.get('/stats/summary');
  return res.data;
});

export const fetchGenderStats = createAsyncThunk('stats/fetchGenderStats', async () => {
  const res = await api.get('/stats/gender');
  return res.data;
});

export const fetchChronicConditions = createAsyncThunk('stats/fetchChronicConditions', async () => {
  const res = await api.get('/stats/chronic');
  return res.data;
});

export const fetchAdmissions = createAsyncThunk('stats/fetchAdmissions', async () => {
  const res = await api.get('/stats/admissions');
  return res.data;
});

// Slice
const statsSlice = createSlice({
  name: 'stats',
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      // Average Age
      .addCase(fetchAverageAge.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchAverageAge.fulfilled, (state, action: PayloadAction<{ averageAge: number }>) => {
        state.loading = false;
        state.averageAge = action.payload.averageAge;
      })
      .addCase(fetchAverageAge.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch average age';
      })

      // Summary Stats
      .addCase(fetchSummaryStats.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchSummaryStats.fulfilled, (state, action: PayloadAction<SummaryStats>) => {
        state.loading = false;
        state.summary = action.payload;
      })
      .addCase(fetchSummaryStats.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch summary stats';
      })

      // Gender Stats
      .addCase(fetchGenderStats.fulfilled, (state, action: PayloadAction<GenderStat[]>) => {
        state.genderStats = action.payload;
      })

      // Chronic Conditions
      .addCase(fetchChronicConditions.fulfilled, (state, action: PayloadAction<any[]>) => {
        state.chronicConditions = action.payload.map(item => ({
          condition: item.condition ?? 'Unknown',
          count: Number(item.patients) || 0
        }));
      })

      // Admissions
      .addCase(fetchAdmissions.fulfilled, (state, action: PayloadAction<any[]>) => {
        state.admissions = action.payload.map(item => ({
          reason: item.reason ?? 'Unknown',
          count: Number(item.patients) || 0
        }));
      });
  },
});

export default statsSlice.reducer;
