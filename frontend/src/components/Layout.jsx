import React, { useEffect, useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import {
  UploadCloud,
  Receipt,
  Repeat,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  ShieldAlert,
  User,
  Target,
  SlidersHorizontal,
  Bell,
  FileText,
} from 'lucide-react';
import { api } from '../api/client';
import VoiceDock from '../features/voice/VoiceDock';

export default function Layout() {
  const [backendOnline, setBackendOnline] = useState(null);

  useEffect(() => {
    let mounted = true;
    const check = async () => {
      try {
        await api.getHealth();
        if (mounted) setBackendOnline(true);
      } catch (e) {
        if (mounted) setBackendOnline(false);
      }
    };
    check();
    const interval = setInterval(check, 10000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const navItems = [
    { to: '/upload', label: 'Upload', icon: UploadCloud },
    { to: '/review', label: 'Transactions', icon: Receipt },
    { to: '/subscriptions', label: 'Subscriptions', icon: Repeat },
    { to: '/profile', label: 'Profile', icon: User },
    { to: '/goals', label: 'Goals', icon: Target },
    { to: '/whatif', label: 'What-If', icon: SlidersHorizontal },
    { to: '/nudges', label: 'Nudges', icon: Bell },
    { to: '/report', label: 'Report', icon: FileText },
  ];

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      {/* Top Navbar */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            {/* Logo */}
            <div className="flex items-center space-x-3 shrink-0">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-600 flex items-center justify-center text-white shadow-md shadow-emerald-500/20">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <span className="text-lg font-bold text-slate-900 tracking-tight flex items-center gap-1.5">
                  Finance Coach <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-emerald-100 text-emerald-800">Integrated</span>
                </span>
                <p className="text-xs text-slate-500">Living Money Model & Intelligent Voice Coach</p>
              </div>
            </div>

            {/* Navigation links */}
            <nav className="hidden lg:flex items-center space-x-1">
              {navItems.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  className={({ isActive }) =>
                    `flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-emerald-50 text-emerald-700 font-semibold shadow-xs'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                    }`
                  }
                >
                  <Icon className="w-4 h-4" />
                  {label}
                </NavLink>
              ))}
            </nav>

            {/* Status indicator */}
            <div className="flex items-center space-x-2">
              <div
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${
                  backendOnline === true
                    ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                    : backendOnline === false
                    ? 'bg-rose-50 text-rose-700 border-rose-200'
                    : 'bg-slate-100 text-slate-600 border-slate-200'
                }`}
                title={backendOnline ? 'Backend API connected at :8000' : 'Cannot reach backend at :8000'}
              >
                {backendOnline === true ? (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                    <span>API Online</span>
                  </>
                ) : backendOnline === false ? (
                  <>
                    <AlertCircle className="w-3.5 h-3.5 text-rose-600" />
                    <span>API Offline</span>
                  </>
                ) : (
                  <span>Checking...</span>
                )}
              </div>
            </div>
          </div>

          {/* Sub-nav for smaller screens */}
          <div className="flex lg:hidden overflow-x-auto py-2 border-t border-slate-100 gap-1 scrollbar-none">
            {navItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium whitespace-nowrap transition-colors ${
                    isActive
                      ? 'bg-emerald-100 text-emerald-800 font-semibold'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                  }`
                }
              >
                <Icon className="w-3.5 h-3.5" />
                {label}
              </NavLink>
            ))}
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 pb-32">
        <Outlet />
      </main>

      {/* Floating Voice Layer */}
      <VoiceDock />

      {/* Footer with Guardrail & Disclaimer */}
      <footer className="bg-white border-t border-slate-200 py-6 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-1.5 text-slate-600 font-medium">
            <ShieldAlert className="w-4 h-4 text-amber-500" />
            <span>Educational modelling only — Not financial advice. Zero real data stored.</span>
          </div>
          <div className="text-slate-400">
            Pipeline: Statement Ingest • Auto-Categorize • Rule Correction • Living Money Model • Wispr Voice
          </div>
        </div>
      </footer>
    </div>
  );
}
