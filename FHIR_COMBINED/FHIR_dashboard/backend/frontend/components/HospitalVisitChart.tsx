// components/HospitalVisitChart.tsx
import React from 'react';
import { Bar } from 'react-chartjs-2';
import { motion } from 'framer-motion';

interface VisitData {
  label: string;
  value: number;
}

interface Props {
  visitData: VisitData[];
  avgLengthOfStay: number | null;
  avgTimeBetweenVisits: number | null; // 
}

const HospitalVisitChart: React.FC<Props> = ({
  visitData,
  avgLengthOfStay,
  avgTimeBetweenVisits,
}) => {
  const chartData = {
    labels: visitData.map((d) => d.label),
    datasets: [
      {
        label: 'Visit Count',
        data: visitData.map((d) => d.value),
        backgroundColor: '#10B981', // Green color
        borderColor: '#10B981',
        borderWidth: 1,
        borderRadius: 4,
        hoverBackgroundColor: '#059669',
        hoverBorderColor: '#059669',
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    plugins: {
      title: {
        display: false, // We'll use our custom header instead
      },
      legend: {
        display: false, // Hide default legend
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        title: { display: true, text: 'Visits' },
        ticks: { stepSize: 1 },
        grid: {
          color: '#E2E8F0',
          borderColor: '#E2E8F0',
        },
        border: {
          color: '#E2E8F0',
        },
      },
      x: {
        title: { display: true, text: 'Month' },
        grid: {
          color: '#E2E8F0',
          borderColor: '#E2E8F0',
        },
        border: {
          color: '#E2E8F0',
        },
      },
    },
  };

  const chartVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.5, ease: "easeOut" as const }
    }
  };

  return (
    <motion.div 
      variants={chartVariants}
      initial="hidden"
      animate="visible"
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
      
      {/* Content */}
      <div className="relative z-10 p-6">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="w-2 h-2 bg-sidebar-accent rounded-full group-hover:scale-125 transition-transform duration-300"></div>
          <h3 className="text-lg font-semibold text-slate-800 group-hover:text-sidebar-accent transition-colors duration-300">
            Hospital Visit Frequency - 2024
          </h3>
        </div>
        
        {/* Chart */}
        {visitData.every((d) => d.value === 0) ? (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.3 }}
            className="text-center text-slate-500 py-8"
          >
            <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-3">
              <svg className="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
              </svg>
            </div>
            <p className="text-slate-500">No hospital visits found for 2024.</p>
          </motion.div>
        ) : (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.1, duration: 0.4 }}
          >
            <Bar data={chartData} options={chartOptions} />
          </motion.div>
        )}

        {/* Stats Row */}
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.4 }}
          className="mt-6 text-sm text-center text-slate-600 flex flex-col md:flex-row gap-2 justify-center"
        >
          <span className="px-3 py-2 bg-slate-50 rounded-lg border border-slate-200">
            Avg Length of Stay:{' '}
            <strong className="text-sidebar-accent">{avgLengthOfStay !== null ? avgLengthOfStay : 'N/A'}</strong> day(s)
          </span>
          <span className="hidden md:inline-block text-slate-300">|</span>
          <span className="px-3 py-2 bg-slate-50 rounded-lg border border-slate-200">
            Avg Time Between Visits:{' '}
            <strong className="text-sidebar-accent">{avgTimeBetweenVisits !== null ? avgTimeBetweenVisits : 'N/A'}</strong> days
          </span>
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
  );
};

export default HospitalVisitChart;
