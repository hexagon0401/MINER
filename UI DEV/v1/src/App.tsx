import { useState, useEffect, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { 
  Shield, 
  ShieldCheck, 
  ShieldAlert, 
  Settings, 
  BarChart3, 
  X, 
  Power, 
  Zap, 
  Lock, 
  Globe,
  Wifi,
  Activity,
  ChevronLeft,
  Moon,
  Sun,
  Monitor,
  LogOut
} from 'lucide-react';

// --- Types ---
type AppState = 'idle' | 'connecting' | 'active' | 'failed' | 'off';
type Panel = 'main' | 'settings' | 'stats' | 'shutdown';
type Theme = 'dark' | 'light' | 'system';

// --- Components ---

const ProgressRing = ({ progress, status, isDark }: { progress: number; status: AppState; isDark: boolean }) => {
  const radius = 90;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (progress / 100) * circumference;

  const getStrokeColor = () => {
    if (status === 'active') return '#00ff9f';
    if (status === 'failed') return '#ff4d4d';
    if (status === 'connecting') return '#4cc9f0';
    return isDark ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)';
  };

  return (
    <svg className="w-64 h-64 -rotate-90 transform">
      <circle
        cx="128"
        cy="128"
        r={radius}
        stroke={isDark ? "rgba(255, 255, 255, 0.05)" : "rgba(0, 0, 0, 0.05)"}
        strokeWidth="4"
        fill="transparent"
      />
      <motion.circle
        cx="128"
        cy="128"
        r={radius}
        stroke={getStrokeColor()}
        strokeWidth="4"
        fill="transparent"
        strokeDasharray={circumference}
        initial={{ strokeDashoffset: circumference }}
        animate={{ strokeDashoffset }}
        transition={{ duration: 0.5, ease: "easeInOut" }}
        strokeLinecap="round"
      />
    </svg>
  );
};

export default function App() {
  const [state, setState] = useState<AppState>('idle');
  const [progress, setProgress] = useState(0);
  const [activePanel, setActivePanel] = useState<Panel>('main');
  const [theme, setTheme] = useState<Theme>('dark');
  const [stats, setStats] = useState({
    latency: 24,
    down: 124.5,
    up: 42.1,
    uptime: '00:00:00'
  });

  // --- Theme Logic ---
  const isDark = useMemo(() => {
    if (theme === 'system') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches;
    }
    return theme === 'dark';
  }, [theme]);

  useEffect(() => {
    const root = window.document.documentElement;
    if (isDark) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }, [isDark]);

  // Handle system theme changes
  useEffect(() => {
    if (theme !== 'system') return;
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = () => {
      const root = window.document.documentElement;
      if (mediaQuery.matches) {
        root.classList.add('dark');
      } else {
        root.classList.remove('dark');
      }
    };
    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, [theme]);

  // Simulation Logic
  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;
    if (state === 'connecting') {
      setProgress(0);
      interval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 100) {
            clearInterval(interval);
            setState('active');
            return 100;
          }
          return prev + 2;
        });
      }, 50);
    } else if (state === 'idle') {
      setProgress(0);
    }
    return () => clearInterval(interval);
  }, [state]);

  // Mock Uptime
  useEffect(() => {
    let start = Date.now();
    const interval = setInterval(() => {
      if (state === 'active') {
        const diff = Date.now() - start;
        const h = Math.floor(diff / 3600000).toString().padStart(2, '0');
        const m = Math.floor((diff % 3600000) / 60000).toString().padStart(2, '0');
        const s = Math.floor((diff % 60000) / 1000).toString().padStart(2, '0');
        setStats(prev => ({ ...prev, uptime: `${h}:${m}:${s}` }));
      } else {
        start = Date.now();
        setStats(prev => ({ ...prev, uptime: '00:00:00' }));
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [state]);

  const handleToggle = useCallback(() => {
    if (state === 'off') return;
    if (state === 'idle' || state === 'failed') {
      setState('connecting');
    } else {
      setState('idle');
    }
  }, [state]);

  const handleQuit = () => {
    setState('off');
    setActivePanel('shutdown');
    // In a real app, this might close the window or exit
  };

  return (
    <div className="relative h-screen w-full overflow-hidden flex flex-col items-center justify-center bg-bg-app text-text-main selection:bg-brand-primary/30 transition-colors duration-500">
      {/* Background Decor */}
      <div className={`absolute inset-0 pointer-events-none transition-opacity duration-1000 overflow-hidden ${state === 'off' ? 'opacity-0' : 'opacity-20'}`}>
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-brand-primary rounded-full blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-brand-secondary rounded-full blur-[120px]" />
      </div>

      <AnimatePresence mode="wait">
        {activePanel === 'main' && (
          <motion.div
            key="main"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 1.05 }}
            transition={{ duration: 0.4, ease: [0.23, 1, 0.32, 1] }}
            className="relative z-10 flex flex-col items-center w-full max-w-sm"
          >
            {/* Top Toolbar */}
            <div className="absolute -top-24 w-full flex justify-between px-4">
               <div className="flex glass rounded-2xl p-1 gap-1">
                 {(['light', 'dark', 'system'] as Theme[]).map(t => (
                   <button 
                    key={t}
                    onClick={() => setTheme(t)}
                    className={`p-2 rounded-xl transition-all ${theme === t ? 'bg-brand-primary text-bg-app' : 'text-text-dim hover:text-text-main'}`}
                   >
                     {t === 'light' && <Sun className="w-4 h-4" />}
                     {t === 'dark' && <Moon className="w-4 h-4" />}
                     {t === 'system' && <Monitor className="w-4 h-4" />}
                   </button>
                 ))}
               </div>
               <button 
                onClick={handleQuit}
                className="glass p-3 rounded-2xl text-brand-danger hover:bg-brand-danger/10 transition-colors group"
               >
                 <LogOut className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
               </button>
            </div>

            {/* Header */}
            <div className="mb-12 text-center">
              <motion.h1 
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                className="text-3xl font-bold tracking-tight mb-2"
              >
                NetShield <span className="text-brand-primary font-mono uppercase tracking-tighter">OS</span>
              </motion.h1>
              <motion.p 
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.1 }}
                className="text-text-dim text-sm font-medium"
              >
                {state === 'off' ? 'System offline' : 'Intelligent DPI Optimization'}
              </motion.p>
            </div>

            {/* Central Button Area */}
            <div className="relative group cursor-pointer" onClick={handleToggle}>
              <motion.div 
                animate={{ 
                  scale: state === 'active' ? [1, 1.02, 1] : 1,
                }}
                transition={{ repeat: Infinity, duration: 4 }}
                className="relative flex items-center justify-center"
              >
                <ProgressRing progress={progress} status={state} isDark={isDark} />
                
                <div className={`absolute inset-4 rounded-full flex flex-col items-center justify-center transition-all duration-700 ${
                  state === 'active' ? 'bg-brand-primary/10 shadow-[inset_0_0_40px_rgba(0,255,159,0.1)]' : 'bg-text-main/5'
                }`}>
                  <AnimatePresence mode="wait">
                    {state === 'idle' && (
                      <motion.div key="idle" initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 1.2 }}>
                        <Shield className="w-16 h-16 text-text-dim" />
                      </motion.div>
                    )}
                    {state === 'connecting' && (
                      <motion.div key="connecting" animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 2, ease: "linear" }}>
                        <Zap className="w-16 h-16 text-brand-secondary" />
                      </motion.div>
                    )}
                    {state === 'active' && (
                      <motion.div key="active" initial={{ opacity: 0, scale: 1.5 }} animate={{ opacity: 1, scale: 1 }}>
                        <ShieldCheck className="w-16 h-16 text-brand-primary" />
                        <motion.div 
                          className="absolute inset-0 bg-brand-primary rounded-full blur-xl opacity-20"
                          animate={{ scale: [1, 1.4, 1], opacity: [0.2, 0.4, 0.2] }}
                          transition={{ repeat: Infinity, duration: 2 }}
                        />
                      </motion.div>
                    )}
                    {state === 'failed' && (
                      <motion.div key="failed" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                        <ShieldAlert className="w-16 h-16 text-brand-danger" />
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </motion.div>

              {/* Status Badge */}
              <motion.div 
                initial={false}
                animate={{ 
                  y: state === 'active' ? 0 : 10,
                  opacity: state === 'active' ? 1 : 0
                }}
                className="absolute -bottom-4 left-1/2 -translate-x-1/2 glass px-4 py-1 rounded-full text-[10px] font-mono font-bold text-brand-primary uppercase tracking-[0.2em]"
              >
                LIVE PROTECTION
              </motion.div>
            </div>

            {/* Bottom Status */}
            <div className="mt-16 text-center space-y-2">
              <motion.div 
                key={state}
                initial={{ y: 5, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                className="text-xl font-semibold transition-colors duration-500"
              >
                {state === 'idle' && 'System Suspended'}
                {state === 'connecting' && 'Establishing Tunnel...'}
                {state === 'active' && 'Optimized Connection'}
                {state === 'failed' && 'Handshake Failed'}
              </motion.div>
              <div className="text-text-dim text-sm h-5 font-mono">
                {state === 'connecting' ? `${progress}% synced` : (state === 'active' ? `Encrypted • ${stats.uptime}` : 'Ready to secure')}
              </div>
            </div>

            {/* Nav Controls */}
            <div className="mt-12 flex gap-4">
              <button 
                onClick={() => setActivePanel('stats')}
                className="glass p-4 rounded-3xl hover:bg-white/10 transition-colors group"
              >
                <BarChart3 className="w-6 h-6 text-text-dim group-hover:text-brand-secondary transition-colors" />
              </button>
              <button 
                onClick={() => setActivePanel('settings')}
                className="glass p-4 rounded-3xl hover:bg-white/10 transition-colors group"
              >
                <Settings className="w-6 h-6 text-text-dim group-hover:text-brand-primary transition-colors" />
              </button>
            </div>
          </motion.div>
        )}

        {/* Panel View: Stats */}
        {activePanel === 'stats' && (
          <motion.div
            key="stats"
            initial={{ x: '100%', opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '100%', opacity: 0 }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="absolute inset-0 z-20 bg-bg-app flex flex-col p-8"
          >
            <div className="flex items-center justify-between mb-8">
              <button onClick={() => setActivePanel('main')} className="flex items-center text-text-dim hover:text-text-main transition-colors">
                <ChevronLeft className="w-5 h-5 mr-1" />
                <span className="font-semibold text-sm">Back</span>
              </button>
              <h2 className="text-xl font-bold">Network Analytics</h2>
              <div className="w-10 h-10 flex items-center justify-center rounded-full glass">
                <Activity className="w-5 h-5 text-brand-primary" />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 flex-1">
              {[
                { label: 'Latency', value: `${stats.latency}ms`, icon: <Wifi className="w-4 h-4 text-brand-secondary" />, sub: 'Stable' },
                { label: 'Download', value: `${stats.down}Mb/s`, icon: <Globe className="w-4 h-4 text-brand-primary" />, sub: 'Peak flow' },
                { label: 'Upload', value: `${stats.up}Mb/s`, icon: <Zap className="w-4 h-4 text-orange-400" />, sub: 'Burst' },
                { label: 'Tunnel', value: 'AES-256', icon: <Lock className="w-4 h-4 text-purple-400" />, sub: 'Verified' },
              ].map((item, i) => (
                <motion.div 
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ delay: i * 0.1 }}
                  key={item.label} 
                  className="glass p-6 rounded-3xl flex flex-col justify-between"
                >
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-text-dim text-[10px] font-bold uppercase tracking-wider">{item.label}</span>
                    {item.icon}
                  </div>
                  <div>
                    <div className="text-xl font-mono font-bold">{item.value}</div>
                    <div className="text-[10px] text-text-dim font-medium">{item.sub}</div>
                  </div>
                </motion.div>
              ))}
              <motion.div 
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.4 }}
                className="col-span-2 glass p-6 rounded-3xl flex items-center justify-between"
              >
                <div>
                  <div className="text-[10px] text-text-dim font-bold uppercase mb-1">Session Duration</div>
                  <div className="text-3xl font-mono font-bold text-brand-primary">{stats.uptime}</div>
                </div>
                <button className="bg-brand-primary/10 text-brand-primary px-4 py-2 rounded-xl border border-brand-primary/20 text-xs font-bold hover:bg-brand-primary/20 transition-colors">
                  Reset
                </button>
              </motion.div>
            </div>
          </motion.div>
        )}

        {/* Panel View: Settings */}
        {activePanel === 'settings' && (
          <motion.div
            key="settings"
            initial={{ x: '-100%', opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '-100%', opacity: 0 }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="absolute inset-0 z-20 bg-bg-app flex flex-col p-8"
          >
            <div className="flex items-center justify-between mb-8">
              <h2 className="text-xl font-bold">Preferences</h2>
              <button 
                 onClick={() => setActivePanel('main')}
                 className="w-10 h-10 flex items-center justify-center rounded-full glass hover:bg-text-main/10 transition-colors"
                >
                <X className="w-5 h-5 text-text-dim" />
              </button>
            </div>

            <div className="space-y-4">
              {[
                { title: 'Bypass Protocol', desc: 'Custom Shadow-TLS logic', active: true },
                { title: 'Auto-Secure', desc: 'Enable on startup', active: false },
                { title: 'UDP Tunneling', desc: 'Improve gaming performance', active: true },
                { title: 'Smart Route', desc: 'Automatic server selection', active: true },
              ].map((item, i) => (
                <motion.div 
                  initial={{ x: -20, opacity: 0 }}
                  animate={{ x: 0, opacity: 1 }}
                  transition={{ delay: i * 0.05 }}
                  key={item.title} 
                  className="flex items-center justify-between p-4 glass rounded-2xl"
                >
                  <div>
                    <h3 className="font-semibold text-sm">{item.title}</h3>
                    <p className="text-[10px] text-text-dim">{item.desc}</p>
                  </div>
                  <div className={`w-10 h-5 rounded-full relative transition-all duration-300 cursor-pointer ${item.active ? 'bg-brand-primary' : 'bg-text-main/10'}`}>
                    <div className={`absolute top-1 w-3 h-3 rounded-full bg-white transition-all duration-300 ${item.active ? 'left-6' : 'left-1'}`} />
                  </div>
                </motion.div>
              ))}
            </div>

            <div className="mt-auto pt-8">
              <button className="w-full flex items-center justify-center gap-2 p-4 text-brand-danger font-bold text-sm glass hover:bg-brand-danger/10 transition-colors rounded-2xl group">
                <Power className="w-4 h-4 group-hover:rotate-90 transition-transform" />
                Flush Environment
              </button>
            </div>
          </motion.div>
        )}

        {/* Shutdown Panel */}
        {activePanel === 'shutdown' && (
          <motion.div
            key="shutdown"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex flex-col items-center gap-6"
          >
            <motion.div 
               animate={{ scale: [1, 1.1, 1], opacity: [0.5, 1, 0.5] }}
               transition={{ repeat: Infinity, duration: 3 }}
               className="w-24 h-24 rounded-full glass flex items-center justify-center text-text-dim"
            >
              <Power className="w-10 h-10" />
            </motion.div>
            <div className="text-center">
              <h2 className="text-2xl font-bold mb-2">NetShield Offline</h2>
              <p className="text-text-dim text-sm">System resources have been safely released.</p>
            </div>
            <button 
              onClick={() => { setState('idle'); setActivePanel('main'); }}
              className="mt-4 px-8 py-3 bg-brand-primary text-bg-app font-bold rounded-2xl hover:scale-105 active:scale-95 transition-all shadow-xl shadow-brand-primary/20"
            >
              Relaunch System
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}


