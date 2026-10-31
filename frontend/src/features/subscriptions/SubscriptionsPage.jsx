import React, { useEffect, useRef, useState, useMemo } from 'react';
import {
  Repeat,
  AlertTriangle,
  CheckCircle,
  EyeOff,
  Calendar,
  CreditCard,
  RefreshCw,
  TrendingUp,
  DollarSign,
  ArrowRight,
  ShieldCheck,
} from 'lucide-react';
import { api } from '../../api/client';
import { useToast } from '../../components/Toast';

export default function SubscriptionsPage() {
  const { addToast } = useToast();

  const [subscriptions, setSubscriptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionInProgress, setActionInProgress] = useState(null);
  const [statusFilter, setStatusFilter] = useState('all'); // 'all' | 'active' | 'changed' | 'unused'

  const loadSubscriptions = async () => {
    setLoading(true);
    try {
      const data = await api.getRecurring();
      setSubscriptions(Array.isArray(data) ? data : []);
    } catch (err) {
      addToast({
        type: 'error',
        title: 'Failed to Load Subscriptions',
        message: err.message,
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSubscriptions();
  }, []);

  // Reload when another part of the app (e.g. the voice bar) changes data.
  const reloadRef = useRef(loadSubscriptions);
  reloadRef.current = loadSubscriptions;
  useEffect(() => {
    const onChange = () => reloadRef.current();
    window.addEventListener('data-changed', onChange);
    return () => window.removeEventListener('data-changed', onChange);
  }, []);

  const handleMarkUnused = async (sub) => {
    if (!sub.merchant_hash) return;

    setActionInProgress(sub.merchant_hash);
    try {
      await api.markRecurringUnused(sub.merchant_hash);
      addToast({
        type: 'success',
        title: 'Subscription Marked Unused',
        message: `${sub.merchant} was flagged as unused. Future nudges will highlight potential savings.`,
      });
      // Refresh list
      await loadSubscriptions();
    } catch (err) {
      addToast({
        type: 'error',
        title: 'Action Failed',
        message: err.message || 'Could not mark subscription unused.',
      });
    } finally {
      setActionInProgress(null);
    }
  };

  // KPIs
  const stats = useMemo(() => {
    let monthlySpend = 0;
    let activeCount = 0;
    let changedCount = 0;
    let unusedCount = 0;

    subscriptions.forEach((s) => {
      const amt = parseFloat(s.amount) || 0;
      if (s.status === 'active' || s.status === 'changed') {
        monthlySpend += amt;
      }
      if (s.status === 'active') activeCount++;
      if (s.status === 'changed') changedCount++;
      if (s.status === 'unused') unusedCount++;
    });

    return {
      monthlySpend,
      activeCount,
      changedCount,
      unusedCount,
      totalCount: subscriptions.length,
    };
  }, [subscriptions]);

  // Changed items for alerts
  const priceHikeItems = useMemo(
    () => subscriptions.filter((s) => s.status === 'changed'),
    [subscriptions]
  );

  // Filtered subscriptions
  const filteredSubs = useMemo(() => {
    if (statusFilter === 'all') return subscriptions;
    return subscriptions.filter((s) => s.status === statusFilter);
  }, [subscriptions, statusFilter]);

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Recurring & Subscriptions
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Automatic recurring charge detection (F4 engine) with price-change alerts and unused subscription tracking.
          </p>
        </div>

        <button
          onClick={loadSubscriptions}
          className="flex items-center gap-2 px-3 py-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-lg shadow-2xs transition-colors self-start sm:self-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-sky-600' : ''}`} />
          Refresh Detection
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs">
          <span className="text-xs font-medium text-slate-500">Monthly Subscriptions Spend</span>
          <p className="text-2xl font-extrabold text-slate-900 mt-1">
            ₹{stats.monthlySpend.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
          <span className="text-[11px] text-slate-400 mt-0.5 block">Estimated 30-day recurring cost</span>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs">
          <span className="text-xs font-medium text-slate-500">Active Subscriptions</span>
          <p className="text-2xl font-extrabold text-emerald-600 mt-1 flex items-center gap-1.5">
            {stats.activeCount}
            <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-medium">
              Healthy
            </span>
          </p>
          <span className="text-[11px] text-slate-400 mt-0.5 block">Regular cadence confirmed</span>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs">
          <span className="text-xs font-medium text-slate-500">Price Hike Alerts</span>
          <p className="text-2xl font-extrabold text-amber-600 mt-1 flex items-center gap-1.5">
            {stats.changedCount}
            {stats.changedCount > 0 && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 font-medium animate-pulse">
                Action Needed
              </span>
            )}
          </p>
          <span className="text-[11px] text-slate-400 mt-0.5 block">&gt;5% change from baseline</span>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs">
          <span className="text-xs font-medium text-slate-500">Unused Subscriptions</span>
          <p className="text-2xl font-extrabold text-slate-600 mt-1 flex items-center gap-1.5">
            {stats.unusedCount}
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 font-medium">
              Flagged
            </span>
          </p>
          <span className="text-[11px] text-slate-400 mt-0.5 block">Opportunity for savings</span>
        </div>
      </div>

      {/* Price Change Alert Banner */}
      {priceHikeItems.length > 0 && (
        <div className="bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-300 rounded-2xl p-5 shadow-xs space-y-3">
          <div className="flex items-start gap-3">
            <div className="p-2 bg-amber-500 text-white rounded-xl shadow-xs">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div className="flex-1">
              <h3 className="text-sm font-bold text-amber-950 flex items-center gap-2">
                Price Hike Alert Detected
                <span className="px-2 py-0.5 rounded-full text-[11px] bg-amber-200 text-amber-900 font-semibold">
                  {priceHikeItems.length} subscription{priceHikeItems.length > 1 ? 's' : ''}
                </span>
              </h3>
              <p className="text-xs text-amber-800 mt-1">
                The recurring engine detected that latest charges deviated from past recurring amounts by more than 5%.
              </p>

              <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {priceHikeItems.map((sub) => (
                  <div
                    key={sub.merchant}
                    className="bg-white/80 border border-amber-200 rounded-xl p-3 flex items-center justify-between"
                  >
                    <div>
                      <span className="text-xs font-bold text-slate-900 block">{sub.merchant}</span>
                      <span className="text-[11px] text-slate-500">
                        Cadence: {sub.cadence} • Last: {sub.last_seen}
                      </span>
                    </div>
                    <div className="text-right">
                      <span className="text-xs font-bold text-amber-700">₹{parseFloat(sub.amount).toFixed(2)}</span>
                      <span className="block text-[10px] text-amber-600 font-medium">Changed</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Subscriptions Grid & Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-2xs p-6 space-y-6">
        {/* Filter Tabs */}
        <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-100">
          <div className="flex items-center space-x-2">
            <span className="text-xs font-semibold text-slate-500 mr-1">Status:</span>
            {[
              { id: 'all', label: `All (${subscriptions.length})` },
              { id: 'active', label: `Active (${stats.activeCount})` },
              { id: 'changed', label: `Price Changed (${stats.changedCount})` },
              { id: 'unused', label: `Unused (${stats.unusedCount})` },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setStatusFilter(tab.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  statusFilter === tab.id
                    ? 'bg-sky-600 text-white shadow-xs'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <span className="text-xs text-slate-400">
            Detected over 3+ occurrences at regular cadence
          </span>
        </div>

        {/* Content */}
        {loading ? (
          <div className="py-16 text-center text-slate-400">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-sky-600" />
            Scanning recurring patterns...
          </div>
        ) : filteredSubs.length === 0 ? (
          <div className="py-16 text-center text-slate-500 space-y-2">
            <Repeat className="w-8 h-8 mx-auto text-slate-300" />
            <p className="text-sm font-medium">No recurring subscriptions match this filter.</p>
            <p className="text-xs text-slate-400">
              Upload bank statements with at least 3 regular transactions to detect subscriptions automatically.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredSubs.map((sub) => {
              const isChanged = sub.status === 'changed';
              const isUnused = sub.status === 'unused';
              const isActive = sub.status === 'active';
              const isMarking = actionInProgress === sub.merchant_hash;

              return (
                <div
                  key={sub.merchant}
                  className={`rounded-2xl border p-5 transition-all flex flex-col justify-between ${
                    isChanged
                      ? 'border-amber-300 bg-amber-50/30 shadow-xs'
                      : isUnused
                      ? 'border-slate-300 bg-slate-50/70 opacity-80'
                      : 'border-slate-200 bg-white hover:border-sky-300 hover:shadow-xs'
                  }`}
                >
                  <div className="space-y-3">
                    {/* Top Row: Merchant + Status Badge */}
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h4 className={`text-base font-bold ${isUnused ? 'text-slate-600 line-through' : 'text-slate-900'}`}>
                          {sub.merchant}
                        </h4>
                        <span className="text-xs font-medium text-slate-500 capitalize">
                          {sub.cadence} Cadence
                        </span>
                      </div>

                      <span
                        className={`px-2.5 py-1 rounded-full text-xs font-semibold uppercase tracking-wider ${
                          isChanged
                            ? 'bg-amber-100 text-amber-800 border border-amber-300'
                            : isUnused
                            ? 'bg-slate-200 text-slate-700 border border-slate-300'
                            : 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                        }`}
                      >
                        {sub.status}
                      </span>
                    </div>

                    {/* Amount */}
                    <div className="pt-2">
                      <span className="text-xs text-slate-400 block font-medium">Charge Amount</span>
                      <span className="text-2xl font-black text-slate-900">
                        ₹{parseFloat(sub.amount).toLocaleString('en-IN', {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })}
                      </span>
                    </div>

                    {/* Dates Info */}
                    <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-200/60 text-xs space-y-1">
                      <div className="flex justify-between text-slate-600">
                        <span className="text-slate-400">Last Charged:</span>
                        <span className="font-mono font-medium">{sub.last_seen || '—'}</span>
                      </div>
                      <div className="flex justify-between text-slate-600">
                        <span className="text-slate-400">Next Expected:</span>
                        <span className="font-mono font-medium text-sky-700">
                          {sub.next_expected || '—'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="pt-4 mt-3 border-t border-slate-100 flex items-center justify-between">
                    {isUnused ? (
                      <span className="text-xs text-slate-400 flex items-center gap-1">
                        <EyeOff className="w-3.5 h-3.5" />
                        Marked as Unused
                      </span>
                    ) : (
                      <button
                        onClick={() => handleMarkUnused(sub)}
                        disabled={isMarking}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors disabled:opacity-50"
                      >
                        {isMarking ? (
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <EyeOff className="w-3.5 h-3.5 text-slate-500" />
                        )}
                        Mark as Unused
                      </button>
                    )}

                    {isChanged && (
                      <span className="text-[11px] font-semibold text-amber-700 flex items-center gap-1">
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                        Price Hike
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
