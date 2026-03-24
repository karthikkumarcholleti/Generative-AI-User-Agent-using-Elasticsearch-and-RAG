import React, { useEffect, useMemo } from 'react';
import { useAppDispatch, useAppSelector } from '@/redux/hooks';
import {
  getAllPatients,
  getDashboardData,
  setPatientId,
} from '@/redux/conditionsSlice';
import Sidebar from '@/components/Sidebar';
import Select from 'react-select';
import { motion } from 'framer-motion';
import PatientSearch from '@/components/PatientSearch';
import {
  Chart as ChartJS,
  BarElement,
  CategoryScale,
  LinearScale,  
  Tooltip,
  Title,
  Legend
} from 'chart.js';

ChartJS.register(
  BarElement,
  CategoryScale,
  LinearScale,   
  Tooltip,
  Title,
  Legend
);

import ConditionsAndComorbiditiesTable from '@/components/ConditionsAndComorbiditiesTable';
import HospitalVisitChart from '@/components/HospitalVisitChart';

const getMonthlyVisitDataFor2024 = (rawData: Record<string, number>) => {
  const monthLabels = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December',
  ];

  return monthLabels.map((label, idx) => {
    const key = `2024-${String(idx + 1).padStart(2, '0')}`;
    return {
      label,
      value: rawData[key] || 0,
    };
  });
};

export default function ConditionsPage() {
  const dispatch = useAppDispatch();
  const { patientList, patientId, dashboardData } = useAppSelector(
    (state) => state.conditions
  );

  const formattedPatients = useMemo(() => {
    return patientList.map((p) => ({
      value: p.patient_id,
      label: `Patient ${parseInt(p.patient_id, 10)}`,
    }));
  }, [patientList]);

  useEffect(() => {
    dispatch(getAllPatients());
  }, [dispatch]);

  useEffect(() => {
    if (formattedPatients.length && !patientId) {
      const defaultId = formattedPatients[0].value;
      dispatch(setPatientId(defaultId));
    }
  }, [formattedPatients, patientId, dispatch]);

  useEffect(() => {
    if (patientId) {
      dispatch(getDashboardData(patientId));
    }
  }, [patientId, dispatch]);

  const handlePatientChange = (selected: any) => {
    const id = selected?.value;
    dispatch(setPatientId(id));
  };

  const visitData = useMemo(
    () => getMonthlyVisitDataFor2024(dashboardData?.monthly_visits || {}),
    [dashboardData?.monthly_visits]
  );

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
      transition: { duration: 0.4, ease: "easeOut" as const }
    }
  };

  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar />
      <main className="flex-1 bg-white">
        {/* Sticky Page Header */}
        <motion.header 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="sticky top-0 z-10 bg-white/95 backdrop-blur-sm border-b border-slate-200/60 shadow-sm"
        >
          <div className="px-8 py-6">
            <h1 className="text-3xl font-bold text-slate-800 tracking-tight">
              Conditions & Comorbidities
            </h1>
            <p className="text-slate-600 mt-1">Patient Health Analysis & Healthcare Seeking Behavior</p>
          </div>
        </motion.header>

        {/* Main Content Area */}
        <motion.div 
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="p-6 space-y-6"
        >
          {/* Patient Selection Section */}
          <motion.section variants={itemVariants} className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-1 h-8 bg-sidebar-accent rounded-full"></div>
              <h2 className="text-xl font-semibold text-slate-800">Patient Selection</h2>
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
                  duration: 3, 
                  ease: "easeInOut", 
                  repeat: Infinity, 
                  repeatDelay: 4 
                }}
                className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-sidebar-accent to-sidebar-accent-hover"
              />
              
              {/* Hover Glow Effect */}
              <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-sidebar-accent/5 to-sidebar-accent-hover/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
              
              <div className="relative z-10 flex flex-col xl:flex-row flex-wrap xl:flex-nowrap items-start xl:items-center gap-6 w-full">
                <div className="w-full sm:w-72 md:w-80 xl:w-64">
                  <label className="text-sm font-semibold text-slate-700 mb-2 block">
                    Search Patient:
                  </label>
                  
                  <PatientSearch
                    value={patientId}
                    onChange={(id) => handlePatientChange({ value: id })}
                    placeholder="Search by name or ID..."
                  />
                </div>

                <div className="text-center xl:text-left flex-1 min-w-[240px]">
                  <h2 className="text-lg font-bold text-slate-800">
                    Conditions, Healthcare Seeking Behavior & Recommendations
                  </h2>
                </div>

                <motion.div 
                  whileHover={{ scale: 1.05 }}
                  className="text-center xl:text-right xl:ml-auto text-lg font-semibold text-green-700 bg-green-100 px-4 py-2 rounded-lg border border-green-200 shadow-sm w-full sm:w-auto"
                >
                  {dashboardData?.name || 'N/A'}
                </motion.div>
              </div>
              
              {/* Decorative Background Elements */}
              <div className="absolute top-4 right-4 opacity-5 group-hover:opacity-10 transition-opacity duration-500">
                <div className="w-16 h-16 bg-sidebar-accent rounded-full"></div>
              </div>
              <div className="absolute bottom-4 right-8 opacity-5 group-hover:opacity-10 transition-opacity duration-500">
                <div className="w-8 h-8 bg-sidebar-accent rounded-full"></div>
              </div>
            </motion.div>
          </motion.section>

          {/* Table Component */}
          <motion.section variants={itemVariants}>
            <ConditionsAndComorbiditiesTable
              groupedConditions={dashboardData?.groupedConditions || []}
              conditionStats={dashboardData?.conditionStats ?? undefined}
            />
          </motion.section>

          {/* Chart Component */}
          <motion.section variants={itemVariants}>
            <HospitalVisitChart
              visitData={visitData}
              avgLengthOfStay={Number(dashboardData?.avg_length_of_stay ?? 0)}
              avgTimeBetweenVisits={Number(dashboardData?.avg_time_between_visits ?? 0)}
            />
          </motion.section>
        </motion.div>
      </main>
    </div>
  );
}
