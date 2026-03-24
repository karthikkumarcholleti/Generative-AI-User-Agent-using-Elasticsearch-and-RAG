import { useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '@/redux/hooks';
import {
  fetchGenderStats,
  fetchChronicConditions,
  fetchAdmissions,
} from '@/redux/statsSlice';
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  BarChart, XAxis, YAxis, Bar, CartesianGrid, Legend
} from 'recharts';
import DashboardCard from './DashboardCard';
import { motion } from 'framer-motion';

const PIE_COLORS = ['#0EA5E9', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4', '#84CC16'];
const BAR_COLORS = ['#0EA5E9'];

export default function DashboardCharts() {
  const dispatch = useAppDispatch();
  const { genderStats, chronicConditions, admissions, averageAge } = useAppSelector((state) => state.stats);

  useEffect(() => {
    dispatch(fetchGenderStats());
    dispatch(fetchChronicConditions());
    dispatch(fetchAdmissions());
  }, [dispatch]);

  const chartVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.5, ease: "easeOut" as const }
    }
  };

  const PremiumChartCard = ({ children, title, className = "" }: { children: React.ReactNode; title: string; className?: string }) => (
    <motion.div 
      variants={chartVariants}
      initial="hidden"
      animate="visible"
      whileHover={{ y: -2, scale: 1.01 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className={`group relative bg-gradient-to-br from-white via-slate-50/30 to-slate-100/20 p-6 rounded-2xl shadow-lg border-2 border-slate-300/60 hover:shadow-2xl hover:border-sidebar-accent/60 transition-all duration-500 overflow-hidden ${className}`}
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
      <div className="relative z-10">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-2 h-2 bg-sidebar-accent rounded-full group-hover:scale-125 transition-transform duration-300"></div>
          <h3 className="text-lg font-semibold text-slate-800 group-hover:text-sidebar-accent transition-colors duration-300">
            {title}
          </h3>
        </div>
        {children}
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

  return (
    <div className="space-y-8">
      {/* Section Header */}
      <div className="flex items-center gap-3">
        <div className="w-1 h-8 bg-sidebar-accent rounded-full"></div>
        <h2 className="text-xl font-semibold text-slate-800">Analytics & Insights</h2>
      </div>

      {/* Average Age Card */}
      <motion.div 
        variants={chartVariants}
        initial="hidden"
        animate="visible"
        className="xl:col-span-2"
      >
        <DashboardCard
          title="Average Age"
          value={averageAge ? `${averageAge} years` : 'Loading...'}
        />
      </motion.div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
        {/* Gender Donut Chart */}
        <PremiumChartCard title="Gender Breakdown">
          <div className="w-full max-w-xl mx-auto">
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={genderStats}
                  dataKey="count"
                  nameKey="gender"
                  cx="40%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={80}
                  paddingAngle={3}
                  label={({ name, percent }) =>
                    percent !== undefined ? `${(percent * 100).toFixed(1)}%` : ''
                  }
                  isAnimationActive
                >
                  {genderStats.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{
                    backgroundColor: 'white',
                    border: '1px solid #E2E8F0',
                    borderRadius: '8px',
                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                  }}
                />
                <Legend
                  verticalAlign="middle"
                  align="right"
                  layout="vertical"
                  wrapperStyle={{ fontSize: '12px' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </PremiumChartCard>

        {/* Top Admission Reasons */}
        <PremiumChartCard title="Top Admission Reasons">
          <div className="w-full max-w-3xl mx-auto">
            <ResponsiveContainer width="100%" height={320}>
              <PieChart>
                <Pie
                  data={admissions.slice(0, 7)}
                  dataKey="count"
                  nameKey="reason"
                  cx="50%"
                  cy="46%"
                  outerRadius={110}
                  label={({ percent }) =>
                    percent !== undefined ? `${(percent * 100).toFixed(1)}%` : ''
                  }
                  labelLine={false}
                  isAnimationActive
                >
                  {admissions.slice(0, 7).map((_, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={PIE_COLORS[index % PIE_COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip 
                  formatter={(value: number, name: string, props: any) => [`${value} patients`, props?.payload?.reason ?? name]}
                  contentStyle={{
                    backgroundColor: 'white',
                    border: '1px solid #E2E8F0',
                    borderRadius: '8px',
                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                  }}
                />
                <Legend
                  verticalAlign="bottom"
                  align="center"
                  layout="horizontal"
                  wrapperStyle={{ fontSize: '12px', marginTop: 6 }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </PremiumChartCard>
      </div>

      {/* Top Chronic Conditions */}
      <PremiumChartCard title="Top Chronic Conditions" className="xl:col-span-2">
        {(() => {
          const rows = Math.max(1, chronicConditions.length);
          const rowHeight = 30;
          const chartHeight = Math.min(900, rows * rowHeight + 80);

          return (
            <ResponsiveContainer width="100%" height={chartHeight}>
              <BarChart
                data={chronicConditions}
                layout="vertical"
                margin={{ top: 20, right: 50, left: 180, bottom: 20 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis type="number" allowDecimals={false} stroke="#64748B" />
                <YAxis
                  dataKey="condition"
                  type="category"
                  width={260}
                  interval={0}
                  tick={{ fontSize: 13, fill: '#475569' }}
                />
                <Tooltip
                  formatter={(value: number) => [`${value} patients`, 'Count']}
                  labelStyle={{ fontWeight: 'bold' }}
                  contentStyle={{
                    backgroundColor: 'white',
                    border: '1px solid #E2E8F0',
                    borderRadius: '8px',
                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                  }}
                />
                <Legend />
                <Bar
                  dataKey="count"
                  fill="#0EA5E9"
                  barSize={16}
                  radius={[4, 4, 0, 0]}
                  isAnimationActive
                />
              </BarChart>
            </ResponsiveContainer>
          );
        })()}
      </PremiumChartCard>
    </div>
  );
}
