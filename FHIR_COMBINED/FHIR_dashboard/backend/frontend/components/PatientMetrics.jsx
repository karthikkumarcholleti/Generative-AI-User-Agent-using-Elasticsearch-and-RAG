import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import PatientSearch from './PatientSearch';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Card, CardContent } from '@/components/ui/card';

const metricLabels = {
  heart_rate: 'Heart Rate (bpm)',
  resp_rate: 'Respiratory Rate (bpm)',
  bmi: 'Body Mass Index',
  bp_sys: 'Systolic BP (mmHg)',
  bp_dia: 'Diastolic BP (mmHg)',
  oxygen: 'Oxygen Saturation (%)',
};

const chartColors = {
  heart_rate: '#0EA5E9',     // Sky Blue (medical)
  resp_rate: '#10B981',      // Green (medical)
  bmi: '#F59E0B',            // Amber (medical)
  bp_sys: '#8B5CF6',         // Purple (medical)
  bp_dia: '#EF4444',         // Red (medical)
  oxygen: '#06B6D4',         // Cyan (medical)
};

export default function PatientMetrics() {
  const [metrics, setMetrics] = useState({});
  const [patientId, setPatientId] = useState('');
  const [patientOptions, setPatientOptions] = useState([]);

  useEffect(() => {
    fetchData();
  }, [patientId]);

  const fetchData = async () => {
    try {
      console.log('🔍 Frontend: Fetching data for patient_id:', patientId);
      
      const response = await axios.get('http://localhost:5000/api/metrics/patient-observations', {
        params: patientId ? { patient_id: patientId } : {},
      });
      
      console.log('🔍 Frontend: API Response:', response.data);
      console.log('🔍 Frontend: Response keys:', Object.keys(response.data));
      
      setMetrics(response.data);

      const uniquePatients = new Set();
      Object.values(response.data).forEach((obsList) => {
        obsList.forEach((obs) => uniquePatients.add(String(obs.patient_id)));
      });
      
      console.log('🔍 Frontend: Unique patients found:', [...uniquePatients]);
      setPatientOptions([...uniquePatients]);
    } catch (error) {
      console.error('❌ Frontend: Error fetching metrics:', error);
    }
  };

  const sortedPatientOptions = useMemo(() => {
    return [...patientOptions].sort((a, b) => {
      const aVal = parseInt(a, 10);
      const bVal = parseInt(b, 10);
      if (!Number.isNaN(aVal) && !Number.isNaN(bVal)) {
        return aVal - bVal;
      }
      return String(a).localeCompare(String(b), undefined, {
        numeric: true,
        sensitivity: 'base',
      });
    });
  }, [patientOptions]);

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        duration: 0.6,
        staggerChildren: 0.1
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.4, ease: "easeOut" }
    }
  };

  return (
    <motion.div 
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="p-6 space-y-8"
    >
      {/* Header Section */}
      <motion.div variants={itemVariants} className="space-y-6">
        <div className="flex items-center gap-3">
          <div className="w-1 h-8 bg-sidebar-accent rounded-full"></div>
          <h2 className="text-xl font-semibold text-slate-800">Patient Metrics Overview</h2>
        </div>
        
        <motion.div 
          whileHover={{ y: -2, scale: 1.01 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
          className="group relative bg-gradient-to-br from-white via-slate-50/30 to-slate-100/20 rounded-2xl shadow-lg border-2 border-slate-300/60 p-6 hover:shadow-2xl hover:border-sidebar-accent/60 transition-all duration-500 overflow-hidden"
        >
          {/* Animated Accent Strip */}
          <motion.div 
            initial={{ x: '-100%' }}
            animate={{ x: '100%' }}
            transition={{ 
              duration: 4, 
              ease: "easeInOut", 
              repeat: Infinity, 
              repeatDelay: 5 
            }}
            className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-sidebar-accent to-sidebar-accent-hover"
          />
          
          {/* Hover Glow Effect */}
          <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-sidebar-accent/5 to-sidebar-accent-hover/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
          
          <div className="relative z-10 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <h1 className="text-2xl font-bold text-slate-800">Patient Metrics</h1>
            <div className="w-full sm:w-64">
              <PatientSearch
                value={patientId}
                onChange={(id) => setPatientId(id)}
                placeholder="Search patients or select 'All Patients'..."
              />
            </div>
          </div>
          
          {/* Decorative Background Elements */}
          <div className="absolute top-4 right-4 opacity-5 group-hover:opacity-10 transition-opacity duration-500">
            <div className="w-16 h-16 bg-sidebar-accent rounded-full"></div>
          </div>
          <div className="absolute bottom-4 right-8 opacity-5 group-hover:opacity-10 transition-opacity duration-500">
            <div className="w-8 h-8 bg-sidebar-accent rounded-full"></div>
          </div>
        </motion.div>
      </motion.div>

      {/* Metrics Grid */}
      <motion.div variants={itemVariants} className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {Object.entries(metrics).map(([key, data]) => {
          // Filter data based on selection
          let patientData;
          if (patientId === "") {
            // All Patients - show all data
            patientData = data;
          } else {
            // Specific patient - filter data
            patientData = data.filter(obs => obs.patient_id === patientId);
          }
          
          if (!patientData.length) return null;

          console.log(`🔍 Frontend: Chart ${key} - Total data:`, data.length, 'Filtered data:', patientData.length);

          const maxValue = Math.max(...patientData.map((d) => d.value || 0));
          const customDomain =
            key === 'oxygen'
              ? [maxValue - 30, maxValue + 10]  // center oxygen
              : [0, maxValue + 10];

          return (
            <motion.div
              key={key}
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
              
              <div className="relative z-10 p-6">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-2 h-2 bg-sidebar-accent rounded-full group-hover:scale-125 transition-transform duration-300"></div>
                  <h2 className="text-lg font-semibold text-slate-800 group-hover:text-sidebar-accent transition-colors duration-300">
                    {metricLabels[key] || key}
                    {patientId && patientId !== "" && (
                      <span className="text-sm font-normal text-slate-500 ml-2">(Patient {patientId})</span>
                    )}
                  </h2>
                </div>
                
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={patientData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                    <XAxis
                      dataKey="timestamp"
                      tickFormatter={(tick) => new Date(tick).toLocaleDateString()}
                      angle={-45}
                      textAnchor="end"
                      height={60}
                      tick={{ fontSize: 10, fill: '#64748B' }}
                    />
                    <YAxis
                      domain={customDomain}
                      tick={{ fontSize: 12, fill: '#475569' }}
                      label={{
                        value:
                          (metricLabels[key] &&
                            metricLabels[key].split('(')[1]?.replace(')', '')) ||
                          '',
                        angle: -90,
                        position: 'insideLeft',
                        offset: 10,
                        style: { fill: '#64748B' }
                      }}
                    />
                    <Tooltip
                      formatter={(value, name, props) => [
                        value,
                        `${name} (Patient ${props.payload.patient_id})`,
                      ]}
                      labelFormatter={(label) => new Date(label).toLocaleString()}
                      contentStyle={{
                        backgroundColor: 'white',
                        border: '1px solid #E2E8F0',
                        borderRadius: '8px',
                        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                      }}
                    />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="value"
                      stroke={chartColors[key] || '#10B981'}
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
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
        })}
      </motion.div>
    </motion.div>
  );
}
