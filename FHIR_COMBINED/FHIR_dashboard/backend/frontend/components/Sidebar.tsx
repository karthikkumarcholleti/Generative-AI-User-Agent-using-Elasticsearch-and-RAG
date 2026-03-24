'use client';

import Link from 'next/link';
import { useRouter } from 'next/router';
import { useState, useEffect } from 'react';
import { Menu, X, Home, Activity, Users, Map, Sparkles, MessageCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import styles from './Sidebar.module.css';

export default function Sidebar() {
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const [hasMounted, setHasMounted] = useState(false);
  const [generativeAIMinimized, setGenerativeAIMinimized] = useState(false);
  const [chatMinimized, setChatMinimized] = useState(false);

  useEffect(() => {
    setHasMounted(true);
    
    // Check localStorage for minimized states
    const checkMinimizedStates = () => {
      const savedState = localStorage.getItem('generativeAIState');
      if (savedState) {
        try {
          const parsed = JSON.parse(savedState);
          setGenerativeAIMinimized(parsed.isMinimized || false);
          setChatMinimized(parsed.isChatMinimized || false);
        } catch (e) {
          // Ignore parse errors
        }
      }
    };

    checkMinimizedStates();
    
    // Listen for storage changes (from other tabs/windows)
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'generativeAIState') {
        checkMinimizedStates();
      }
    };
    
    window.addEventListener('storage', handleStorageChange);
    
    // Poll for changes (since same-tab updates don't trigger storage event)
    const interval = setInterval(checkMinimizedStates, 500);
    
    return () => {
      window.removeEventListener('storage', handleStorageChange);
      clearInterval(interval);
    };
  }, []);

  if (!hasMounted) return null;

  const links = [
    { name: 'Dashboard', path: '/', icon: Home },
    { name: 'Conditions & Visits', path: '/conditions', icon: Activity },
    { name: 'Patient Metrics', path: '/metrics', icon: Users },
    { name: 'Disease Hotspots', path: '/disease-hotspots', icon: Map },
    { name: 'Generative AI', path: '/generative-ai', icon: Sparkles, hasIndicator: generativeAIMinimized }
  ];

  const isActive = (path: string) => router.pathname === path;

  return (
    <motion.aside
      initial={{ width: collapsed ? 80 : 256 }}
      animate={{ width: collapsed ? 80 : 256 }}
      transition={{ duration: 0.3, ease: "easeInOut" }}
      className={`min-h-screen bg-gradient-to-br from-sidebar-bg via-sidebar-bg to-sidebar-hover border-r border-sidebar-border shadow-2xl flex flex-col justify-between sticky top-0 backdrop-blur-sm ${styles.sidebar}`}
    >
      {/* Top section: Toggle + Title + Navigation */}
      <div className="px-4 py-6">
        <div className="flex justify-between items-center mb-8">
          <AnimatePresence mode="wait">
            {!collapsed && (
              <motion.h2
                key="title"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.2 }}
                className={`text-2xl font-extrabold tracking-tight text-sidebar-text ${styles.title}`}
              >
                FHIR Dashboard
              </motion.h2>
            )}
          </AnimatePresence>
          
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setCollapsed(!collapsed)}
            className="p-2 rounded-xl bg-sidebar-hover hover:bg-sidebar-border/60 shadow-sm border border-sidebar-border/40 text-sidebar-text hover:text-sidebar-accent transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-sidebar-focus focus:ring-offset-2 focus:ring-offset-sidebar-bg"
            title={collapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
            aria-label={collapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
          >
            <AnimatePresence mode="wait">
              {collapsed ? (
                <motion.div
                  key="menu"
                  initial={{ rotate: -90, opacity: 0 }}
                  animate={{ rotate: 0, opacity: 1 }}
                  exit={{ rotate: 90, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <Menu size={18} />
                </motion.div>
              ) : (
                <motion.div
                  key="close"
                  initial={{ rotate: 90, opacity: 0 }}
                  animate={{ rotate: 0, opacity: 1 }}
                  exit={{ rotate: -90, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <X size={18} />
                </motion.div>
              )}
            </AnimatePresence>
          </motion.button>
        </div>

        <nav className="flex flex-col gap-3" role="navigation" aria-label="Main navigation">
          {links.map((link) => {
            const IconComponent = link.icon;
            const active = isActive(link.path);
            
            return (
              <Link 
                key={link.path} 
                href={link.path} 
                passHref
                onClick={(e) => {
                  // If clicking Generative AI and it's minimized, restore it
                  if (link.name === 'Generative AI' && generativeAIMinimized) {
                    // Clear minimized state in localStorage
                    const savedState = localStorage.getItem('generativeAIState');
                    if (savedState) {
                      try {
                        const parsed = JSON.parse(savedState);
                        parsed.isMinimized = false;
                        localStorage.setItem('generativeAIState', JSON.stringify(parsed));
                      } catch (e) {
                        // Ignore errors
                      }
                    }
                  }
                }}
              >
                <motion.span
                  whileHover={{ x: 4 }}
                  whileTap={{ scale: 0.98 }}
                  className={`group relative block px-4 py-3 rounded-xl cursor-pointer text-sm font-medium transition-all duration-200 ${
                    active
                      ? 'text-sidebar-active-text shadow-lg'
                      : 'text-sidebar-text hover:text-sidebar-accent'
                  }`}
                  title={collapsed ? link.name : ''}
                  role="menuitem"
                  aria-current={active ? 'page' : undefined}
                >
                  {/* Active state background */}
                  {active && (
                    <motion.div
                      layoutId="activeTab"
                      className="absolute inset-0 bg-gradient-to-r from-sidebar-active to-sidebar-accent rounded-xl shadow-lg"
                      initial={false}
                      transition={{ type: "spring", stiffness: 500, damping: 30 }}
                    />
                  )}
                  
                  {/* Content */}
                  <div className="relative z-10 flex items-center gap-3">
                    {collapsed ? (
                      <div className="w-2 h-2 bg-current rounded-full mx-auto opacity-80" />
                    ) : (
                      <>
                        <div className="relative">
                          <IconComponent 
                            size={18} 
                            className={`transition-colors duration-200 ${
                              active ? 'text-sidebar-active-text' : 'text-sidebar-muted group-hover:text-sidebar-accent'
                            }`}
                          />
                          {/* Indicator badge for minimized states */}
                          {link.hasIndicator && (
                            <motion.div
                              initial={{ scale: 0 }}
                              animate={{ scale: 1 }}
                              className="absolute -top-1 -right-1 w-2 h-2 bg-yellow-400 rounded-full border-2 border-sidebar-bg"
                              title="Minimized - Click to restore"
                            />
                          )}
                        </div>
                        <span className="font-medium">{link.name}</span>
                        {/* Generative AI notification when minimized */}
                        {link.name === 'Generative AI' && generativeAIMinimized && (
                          <motion.div
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            className="ml-auto"
                            title="Generative AI minimized - Click to restore"
                          >
                            <Sparkles size={14} className="text-yellow-400" />
                          </motion.div>
                        )}
                        {/* AI Interface notification for chat minimized */}
                        {link.name === 'Generative AI' && chatMinimized && (
                          <motion.div
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            className="ml-auto"
                            title="AI Chat minimized - Click 'AI Interface' to restore"
                          >
                            <MessageCircle size={14} className="text-yellow-400" />
                          </motion.div>
                        )}
                      </>
                    )}
                  </div>
                  
                  {/* Hover effect */}
                  {!active && (
                    <motion.div
                      className="absolute inset-0 bg-sidebar-hover/60 rounded-xl opacity-0 group-hover:opacity-100"
                      initial={false}
                      transition={{ duration: 0.2 }}
                    />
                  )}
                </motion.span>
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Bottom section: Footer */}
      <motion.div
        layout
        className={`text-xs text-sidebar-muted px-4 py-6 border-t border-sidebar-border/40 bg-sidebar-hover/40 backdrop-blur-sm ${styles.footer}`}
      >
        <AnimatePresence mode="wait">
          {!collapsed && (
            <motion.div
              key="footer-text"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
              transition={{ duration: 0.2 }}
              className="text-center"
            >
              © 2025 CoCM Platform
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </motion.aside>
  );
}
