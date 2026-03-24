import { configureStore } from '@reduxjs/toolkit';
import statsReducer from './statsSlice';
import metricsReducer from './metricsSlice';
import conditionsReducer from './conditionsSlice'; 

export const store = configureStore({
  reducer: {
    stats: statsReducer,
    metrics: metricsReducer,
    conditions: conditionsReducer, 
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
