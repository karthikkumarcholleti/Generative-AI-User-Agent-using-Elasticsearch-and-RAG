import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:5000/api', 
  headers: {
    'Content-Type': 'application/json',
  },
});

export default api;

export const fetchDashboardData = async (patientId: string) => {
  const response = await api.get(`/dashboard/${patientId}`);
  return response.data;
};

export const fetchAllPatientIds = async () => {
  const response = await api.get('/patients');
  return response.data;
};

export const fetchHotspotModelMetrics = async () => {
  const response = await api.get('/metrics/hotspot-models');
  return response.data;
};