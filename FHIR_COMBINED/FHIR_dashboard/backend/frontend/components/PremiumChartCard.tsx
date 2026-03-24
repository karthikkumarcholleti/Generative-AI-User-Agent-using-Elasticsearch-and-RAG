import React from 'react';
import { motion } from 'framer-motion';

interface PremiumChartCardProps {
  children: React.ReactNode;
  title?: string;
  className?: string;
}

export default function PremiumChartCard({ children, title, className = "" }: PremiumChartCardProps) {
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
        {title && (
          <div className="flex items-center gap-3 mb-6">
            <div className="w-2 h-2 bg-sidebar-accent rounded-full group-hover:scale-125 transition-transform duration-300"></div>
            <h3 className="text-lg font-semibold text-slate-800 group-hover:text-sidebar-accent transition-colors duration-300">
              {title}
            </h3>
          </div>
        )}
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
}

