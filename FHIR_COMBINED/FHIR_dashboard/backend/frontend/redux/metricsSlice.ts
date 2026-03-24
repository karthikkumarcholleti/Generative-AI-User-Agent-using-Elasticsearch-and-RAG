// redux/metricsSlice.ts
import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import axios from 'axios';

// Define Observation structure
type Observation = {
  patient_id: string;
  value: number;
  timestamp: string | null;
};

interface MetricsState {
  data: {
    [key: string]: Observation[];
  };
  patientOptions: string[];
  loading: boolean;
  error: string | null;
}

// Async fetcher
export const fetchMetrics = createAsyncThunk(
  'metrics/fetchMetrics',
  async (patientId?: string) => {
    const response = await axios.get(
      `http://localhost:5000/api/metrics/patient-observations`,
      { params: patientId ? { patient_id: patientId } : {} }
    );
    return response.data;
  }
);

// Initial state
const initialState: MetricsState = {
  data: {},
  patientOptions: [],
  loading: false,
  error: null,
};

// Slice
const metricsSlice = createSlice({
  name: 'metrics',
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchMetrics.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchMetrics.fulfilled, (state, action) => {
        state.loading = false;
        state.data = action.payload;

        const uniquePatients = new Set<string>();

        
        (Object.values(action.payload) as Observation[][]).forEach((list) =>
          list.forEach((obs) => uniquePatients.add(obs.patient_id))
        );

        state.patientOptions = Array.from(uniquePatients);
      })
      .addCase(fetchMetrics.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message ?? 'Failed to fetch metrics';
      });
  },
});

export default metricsSlice.reducer;
