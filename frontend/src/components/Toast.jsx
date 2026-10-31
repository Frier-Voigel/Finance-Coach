import React, { createContext, useContext, useState, useCallback } from 'react';
import { Sparkles, CheckCircle, AlertTriangle, Info, X } from 'lucide-react';

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((toast) => {
    const id = Date.now() + Math.random().toString(36).substring(2, 9);
    const newToast = { id, ...toast };
    setToasts((prev) => [...prev, newToast]);

    if (!toast.persistent) {
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, toast.duration || 6000);
    }
    return id;
  }, []);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  /**
   * Helper for A3 rule learned toast
   */
  const showRuleLearnedToast = useCallback((rule, pastCount, merchant) => {
    addToast({
      type: 'rule',
      title: 'Rule Learned & Applied!',
      message: `Learned rule: "${rule.pattern || merchant}" → "${rule.category}". Updated ${pastCount} past transaction${pastCount === 1 ? '' : 's'}.`,
      rule,
      pastCount,
      duration: 8000,
    });
  }, [addToast]);

  return (
    <ToastContext.Provider value={{ addToast, removeToast, showRuleLearnedToast }}>
      {children}
      {/* Toast container */}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col space-y-3 max-w-md w-full pointer-events-none">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`pointer-events-auto transform transition-all duration-300 ease-out translate-y-0 opacity-100 p-4 rounded-xl shadow-lg border flex items-start gap-3 ${
              toast.type === 'rule'
                ? 'bg-gradient-to-r from-sky-50 to-indigo-50 border-sky-300 text-slate-800'
                : toast.type === 'success'
                ? 'bg-emerald-50 border-emerald-300 text-emerald-900'
                : toast.type === 'error'
                ? 'bg-rose-50 border-rose-300 text-rose-900'
                : 'bg-white border-slate-200 text-slate-900'
            }`}
          >
            {toast.type === 'rule' ? (
              <div className="p-2 bg-sky-500 rounded-lg text-white shadow-xs">
                <Sparkles className="w-5 h-5 animate-pulse" />
              </div>
            ) : toast.type === 'success' ? (
              <div className="p-2 bg-emerald-500 rounded-lg text-white shadow-xs">
                <CheckCircle className="w-5 h-5" />
              </div>
            ) : toast.type === 'error' ? (
              <div className="p-2 bg-rose-500 rounded-lg text-white shadow-xs">
                <AlertTriangle className="w-5 h-5" />
              </div>
            ) : (
              <div className="p-2 bg-slate-500 rounded-lg text-white shadow-xs">
                <Info className="w-5 h-5" />
              </div>
            )}

            <div className="flex-1 min-w-0">
              <h4 className="text-sm font-semibold text-slate-900">{toast.title}</h4>
              <p className="text-xs text-slate-600 mt-0.5 leading-relaxed">{toast.message}</p>
              {toast.rule && (
                <div className="mt-2 text-xs flex flex-wrap gap-2 items-center bg-white/70 p-2 rounded-lg border border-sky-200">
                  <span className="font-mono bg-sky-100 text-sky-800 px-1.5 py-0.5 rounded">
                    {toast.rule.pattern}
                  </span>
                  <span className="text-slate-400">→</span>
                  <span className="font-semibold text-emerald-700">{toast.rule.category}</span>
                  <span className="text-slate-500 ml-auto text-[11px]">
                    +{toast.pastCount} historical updated
                  </span>
                </div>
              )}
            </div>

            <button
              onClick={() => removeToast(toast.id)}
              className="text-slate-400 hover:text-slate-600 p-1 rounded-md transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within ToastProvider');
  }
  return context;
}
