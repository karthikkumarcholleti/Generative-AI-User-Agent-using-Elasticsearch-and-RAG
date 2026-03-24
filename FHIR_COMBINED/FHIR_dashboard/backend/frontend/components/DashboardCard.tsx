import { motion } from 'framer-motion';
import { TrendingUp, Users, Activity, FileText, Calendar } from 'lucide-react';

type Props = { title: string; value: number | string; };

export default function DashboardCard({ title, value }: Props) {
  // Icon mapping for different metric types
  const getIcon = (title: string) => {
    switch (title.toLowerCase()) {
      case 'patients':
        return <Users size={20} />;
      case 'observations':
        return <Activity size={20} />;
      case 'conditions':
        return <FileText size={20} />;
      case 'encounters':
        return <Calendar size={20} />;
      case 'average age':
        return <TrendingUp size={20} />;
      default:
        return <Activity size={20} />;
    }
  };

  const IconComponent = getIcon(title);

  return (
    <motion.div 
      whileHover={{ y: -2, scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className="group relative bg-gradient-to-br from-white via-slate-50/30 to-slate-100/20 rounded-2xl shadow-lg border-2 border-slate-300/60 p-6 hover:shadow-2xl hover:border-sidebar-accent/60 transition-all duration-500 cursor-pointer overflow-hidden"
    >
      {/* Animated Accent Strip */}
      <motion.div 
        initial={{ x: '-100%' }}
        animate={{ x: '100%' }}
        transition={{ 
          duration: 2, 
          ease: "easeInOut", 
          repeat: Infinity, 
          repeatDelay: 3 
        }}
        className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-sidebar-accent to-sidebar-accent-hover"
      />
      
      {/* Hover Glow Effect */}
      <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-sidebar-accent/5 to-sidebar-accent-hover/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
      
      {/* Content Container */}
      <div className="relative z-10">
        {/* Header Row */}
        <div className="flex items-center justify-between mb-4">
          {/* Icon in Glowing Pill */}
          <div className="relative">
            <motion.div
              whileHover={{ scale: 1.1 }}
              className="w-12 h-12 rounded-full bg-gradient-to-br from-sidebar-accent/20 to-sidebar-accent-hover/20 flex items-center justify-center border border-sidebar-accent/30 group-hover:border-sidebar-accent/60 transition-all duration-300"
            >
              <div className="text-sidebar-accent group-hover:text-sidebar-accent-hover transition-colors duration-300">
                {IconComponent}
              </div>
            </motion.div>
            {/* Glow Effect */}
            <div className="absolute inset-0 rounded-full bg-sidebar-accent/20 blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
          </div>
        </div>
        
        {/* Metric Value */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.4 }}
          className="mb-2"
        >
          <p className="text-3xl font-bold text-slate-800 group-hover:text-sidebar-accent transition-colors duration-300">
            {value}
          </p>
        </motion.div>
        
        {/* Title */}
        <motion.div
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.4 }}
        >
          <h3 className="text-sm font-medium text-slate-600 tracking-wide uppercase">
            {title}
          </h3>
        </motion.div>
      </div>
      
      {/* Decorative Background Elements */}
      <div className="absolute top-4 right-4 opacity-5 group-hover:opacity-10 transition-opacity duration-500">
        <div className="w-16 h-16 bg-sidebar-accent rounded-full"></div>
      </div>
      <div className="absolute bottom-4 right-8 opacity-5 group-hover:opacity-10 transition-opacity duration-500">
        <div className="w-8 h-8 bg-sidebar-accent rounded-full"></div>
      </div>
      
      {/* Subtle Grid Pattern */}
      <div className="absolute inset-0 opacity-[0.02] group-hover:opacity-[0.05] transition-opacity duration-500">
        <div className="w-full h-full" style={{
          backgroundImage: `radial-gradient(circle at 1px 1px, #0EA5E9 1px, transparent 0)`,
          backgroundSize: '20px 20px'
        }} />
      </div>
    </motion.div>
  );
}
