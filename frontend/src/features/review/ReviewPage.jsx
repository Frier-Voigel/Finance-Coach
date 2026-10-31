import React, { useEffect, useState, useMemo } from 'react';
import {
  Search,
  Filter,
  Sparkles,
  BookOpen,
  Trash2,
  X,
  RefreshCw,
  Check,
  AlertCircle,
  TrendingDown,
  TrendingUp,
  SlidersHorizontal,
} from 'lucide-react';
import { api } from '../../api/client';
import { useToast } from '../../components/Toast';

const CATEGORIES = [
  'Food',
  'Transport',
  'Shopping',
  'Entertainment',
  'Utilities',
  'Rent',
  'Salary',
  'Subscriptions',
  'Health',
  'Other',
];

const SOURCES = ['csv', 'pdf', 'sms', 'voice'];

export default function ReviewPage() {
  const { showRuleLearnedToast, addToast } = useToast();

  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [updatingId, setUpdatingId] = useState(null);

  // Filters
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedSource, setSelectedSource] = useState('');
  const [merchantSearch, setMerchantSearch] = useState('');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');

  // Rules Modal
  const [showRulesModal, setShowRulesModal] = useState(false);
  const [rules, setRules] = useState([]);
  const [rulesLoading, setRulesLoading] = useState(false);

  // Load transactions
  const loadTransactions = async () => {
    setLoading(true);
    try {
      const data = await api.getTransactions({
        category: selectedCategory || undefined,
        source: selectedSource || undefined,
        merchant: merchantSearch || undefined,
        from_date: fromDate || undefined,
        to_date: toDate || undefined,
        limit: 200,
      });
      setTransactions(Array.isArray(data) ? data : []);
    } catch (err) {
      addToast({
        type: 'error',
        title: 'Failed to Load Transactions',
        message: err.message,
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTransactions();
  }, [selectedCategory, selectedSource, selectedMerchantQuery(merchantSearch), fromDate, toDate]);

  function selectedMerchantQuery(m) {
    return m.trim();
  }

  // Load Rules
  const loadRules = async () => {
    setRulesLoading(true);
    try {
      const data = await api.getRules();
      setRules(Array.isArray(data) ? data : []);
    } catch (err) {
      addToast({
        type: 'error',
        title: 'Failed to Load Rules',
        message: err.message,
      });
    } finally {
      setRulesLoading(false);
    }
  };

  const handleOpenRules = () => {
    setShowRulesModal(true);
    loadRules();
  };

  const handleDeleteRule = async (ruleId) => {
    try {
      await api.deleteRule(ruleId);
      setRules((prev) => prev.filter((r) => r.id !== ruleId));
      addToast({
        type: 'success',
        title: 'Rule Deleted',
        message: `Categorization rule #${ruleId} was removed.`,
      });
    } catch (err) {
      addToast({
        type: 'error',
        title: 'Failed to Delete Rule',
        message: err.message,
      });
    }
  };

  // Inline Category Edit & Correction Loop (A3)
  const handleCategoryChange = async (txn, newCategory) => {
    if (txn.category === newCategory) return;

    setUpdatingId(txn.id);
    try {
      const result = await api.updateTransactionCategory(txn.id, newCategory);

      // Trigger the A3 "Rule learned" toast
      const rule = result.rule_created || { pattern: txn.merchant, category: newCategory };
      const pastCount = result.past_updated ?? 0;
      showRuleLearnedToast(rule, pastCount, txn.merchant);

      // Refresh list to update all backfilled rows
      await loadTransactions();
    } catch (err) {
      addToast({
        type: 'error',
        title: 'Update Failed',
        message: err.message || 'Could not update category.',
      });
    } finally {
      setUpdatingId(null);
    }
  };

  // Summary KPIs
  const stats = useMemo(() => {
    let debits = 0;
    let credits = 0;
    const merchants = new Set();

    transactions.forEach((t) => {
      const amt = parseFloat(t.amount) || 0;
      if (t.direction === 'debit') debits += amt;
      else credits += amt;
      if (t.merchant) merchants.add(t.merchant);
    });

    return {
      debits,
      credits,
      count: transactions.length,
      merchantsCount: merchants.size,
    };
  }, [transactions]);

  const handleResetFilters = () => {
    setSelectedCategory('');
    setSelectedSource('');
    setMerchantSearch('');
    setFromDate('');
    setToDate('');
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Transactions & Review
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Inline category correction (F3 loop). Fixing a category here automatically teaches a rule and updates past transactions.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleOpenRules}
            className="flex items-center gap-2 px-3.5 py-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-lg shadow-2xs transition-colors"
          >
            <BookOpen className="w-4 h-4 text-sky-600" />
            <span>Learned Rules</span>
            <span className="px-1.5 py-0.2 bg-sky-100 text-sky-800 rounded-full font-mono text-[10px]">
              F3 Engine
            </span>
          </button>

          <button
            onClick={loadTransactions}
            className="p-2 text-slate-600 hover:text-slate-900 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors"
            title="Refresh transactions"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-sky-600' : ''}`} />
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <span className="text-xs font-medium text-slate-500">Total Transactions</span>
          <p className="text-xl font-bold text-slate-900 mt-1">{stats.count}</p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <span className="text-xs font-medium text-slate-500">Total Debits (Spent)</span>
          <p className="text-xl font-bold text-rose-600 mt-1 flex items-center gap-1">
            <TrendingDown className="w-4 h-4" />
            ₹{stats.debits.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <span className="text-xs font-medium text-slate-500">Total Credits (Income)</span>
          <p className="text-xl font-bold text-emerald-600 mt-1 flex items-center gap-1">
            <TrendingUp className="w-4 h-4" />
            ₹{stats.credits.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <span className="text-xs font-medium text-slate-500">Unique Merchants</span>
          <p className="text-xl font-bold text-slate-800 mt-1">{stats.merchantsCount}</p>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs space-y-3">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-700">
          <SlidersHorizontal className="w-3.5 h-3.5 text-sky-600" />
          <span>Filter Transactions</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {/* Merchant Search */}
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
            <input
              type="text"
              placeholder="Search merchant..."
              value={merchantSearch}
              onChange={(e) => setMerchantSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 focus:bg-white"
            />
          </div>

          {/* Category Filter */}
          <div>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 focus:bg-white text-slate-700"
            >
              <option value="">All Categories</option>
              {CATEGORIES.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>

          {/* Source Filter */}
          <div>
            <select
              value={selectedSource}
              onChange={(e) => setSelectedSource(e.target.value)}
              className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 focus:bg-white text-slate-700"
            >
              <option value="">All Sources</option>
              {SOURCES.map((s) => (
                <option key={s} value={s}>
                  Source: {s.toUpperCase()}
                </option>
              ))}
            </select>
          </div>

          {/* From Date */}
          <div>
            <input
              type="date"
              value={fromDate}
              onChange={(e) => setFromDate(e.target.value)}
              title="From date"
              className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 text-slate-700"
            />
          </div>

          {/* To Date */}
          <div className="flex gap-2">
            <input
              type="date"
              value={toDate}
              onChange={(e) => setToDate(e.target.value)}
              title="To date"
              className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 text-slate-700"
            />
            <button
              onClick={handleResetFilters}
              className="px-2.5 py-2 text-xs text-slate-500 hover:text-slate-800 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
              title="Clear all filters"
            >
              Reset
            </button>
          </div>
        </div>
      </div>

      {/* Transactions Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50/80 text-slate-600 font-semibold border-b border-slate-200">
              <tr>
                <th className="py-3 px-4">Date</th>
                <th className="py-3 px-4">Merchant</th>
                <th className="py-3 px-4">Description</th>
                <th className="py-3 px-4">Category (Inline Edit)</th>
                <th className="py-3 px-4">Source</th>
                <th className="py-3 px-4">Type</th>
                <th className="py-3 px-4 text-right">Amount</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading && transactions.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-sky-600" />
                    Loading transactions...
                  </td>
                </tr>
              ) : transactions.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    No transactions found. Upload statements or clear filters.
                  </td>
                </tr>
              ) : (
                transactions.map((txn) => {
                  const isUpdating = updatingId === txn.id;
                  const isUserCorrected = txn.category_source === 'user';
                  const isRuleApplied = txn.category_source === 'rule';
                  const isLlmCategorized = txn.category_source === 'llm';

                  return (
                    <tr
                      key={txn.id}
                      className={`hover:bg-slate-50/80 transition-colors ${
                        isUpdating ? 'bg-sky-50/50' : ''
                      }`}
                    >
                      {/* Date */}
                      <td className="py-3 px-4 font-mono text-slate-600 whitespace-nowrap">
                        {txn.date}
                      </td>

                      {/* Merchant */}
                      <td className="py-3 px-4 font-semibold text-slate-900 whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <span>{txn.merchant || '—'}</span>
                          {txn.account && (
                            <span className="text-[10px] text-slate-400 bg-slate-100 px-1 rounded">
                              {txn.account}
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Description */}
                      <td className="py-3 px-4 text-slate-600 max-w-xs truncate" title={txn.description}>
                        {txn.description}
                      </td>

                      {/* Inline Category Editor */}
                      <td className="py-3 px-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <select
                            value={txn.category || 'Other'}
                            disabled={isUpdating}
                            onChange={(e) => handleCategoryChange(txn, e.target.value)}
                            className={`text-xs font-medium py-1 px-2.5 rounded-lg border transition-all cursor-pointer ${
                              isUserCorrected
                                ? 'bg-purple-50 text-purple-800 border-purple-300 font-semibold'
                                : isRuleApplied
                                ? 'bg-sky-50 text-sky-800 border-sky-300'
                                : isLlmCategorized
                                ? 'bg-amber-50 text-amber-800 border-amber-300'
                                : 'bg-slate-50 text-slate-700 border-slate-300'
                            }`}
                          >
                            {CATEGORIES.map((cat) => (
                              <option key={cat} value={cat}>
                                {cat}
                              </option>
                            ))}
                          </select>

                          {/* Source indicator badge */}
                          <span
                            className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${
                              isUserCorrected
                                ? 'bg-purple-100 text-purple-700'
                                : isRuleApplied
                                ? 'bg-sky-100 text-sky-700'
                                : isLlmCategorized
                                ? 'bg-amber-100 text-amber-700'
                                : 'bg-slate-100 text-slate-500'
                            }`}
                            title={`Category origin: ${txn.category_source}`}
                          >
                            {txn.category_source}
                          </span>

                          {isUpdating && <RefreshCw className="w-3.5 h-3.5 animate-spin text-sky-600" />}
                        </div>
                      </td>

                      {/* File Source */}
                      <td className="py-3 px-4 whitespace-nowrap">
                        <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-700 uppercase">
                          {txn.source}
                        </span>
                      </td>

                      {/* Direction */}
                      <td className="py-3 px-4 whitespace-nowrap">
                        <span
                          className={`px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase ${
                            txn.direction === 'debit'
                              ? 'bg-rose-50 text-rose-700'
                              : 'bg-emerald-50 text-emerald-700'
                          }`}
                        >
                          {txn.direction}
                        </span>
                      </td>

                      {/* Amount */}
                      <td className="py-3 px-4 text-right font-mono font-bold whitespace-nowrap">
                        <span
                          className={txn.direction === 'debit' ? 'text-slate-900' : 'text-emerald-600'}
                        >
                          {txn.direction === 'debit' ? '-' : '+'}₹
                          {parseFloat(txn.amount).toLocaleString('en-IN', {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2,
                          })}
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Footer info */}
        <div className="p-3 bg-slate-50 border-t border-slate-200 text-xs text-slate-500 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-purple-500"></span>
              <span>user (user correction)</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-sky-500"></span>
              <span>rule (learned rule)</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-amber-500"></span>
              <span>llm / default</span>
            </span>
          </div>

          <span>Showing up to {transactions.length} rows</span>
        </div>
      </div>

      {/* Rules Modal (F3 Engine Memory) */}
      {showRulesModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl shadow-xl border border-slate-200 max-w-2xl w-full max-h-[80vh] flex flex-col overflow-hidden animate-fadeIn">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="p-2 bg-sky-100 text-sky-700 rounded-lg">
                  <Sparkles className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900">
                    Learned Categorization Rules
                  </h3>
                  <p className="text-xs text-slate-500">
                    Rules saved in SQLite table <code className="font-mono text-sky-700">rules</code>. Priority order: exact merchant &gt; contains &gt; regex.
                  </p>
                </div>
              </div>

              <button
                onClick={() => setShowRulesModal(false)}
                className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-4 flex-1">
              {rulesLoading ? (
                <div className="py-12 text-center text-slate-400">
                  <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-sky-600" />
                  Loading rules...
                </div>
              ) : rules.length === 0 ? (
                <div className="py-8 text-center text-slate-500">
                  <p className="text-sm font-medium">No custom rules learned yet.</p>
                  <p className="text-xs text-slate-400 mt-1">
                    Edit any transaction category above to trigger the A3 correction loop!
                  </p>
                </div>
              ) : (
                <div className="border border-slate-200 rounded-xl overflow-hidden">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                      <tr>
                        <th className="py-2.5 px-3">Pattern</th>
                        <th className="py-2.5 px-3">Match Type</th>
                        <th className="py-2.5 px-3">Target Category</th>
                        <th className="py-2.5 px-3">Created</th>
                        <th className="py-2.5 px-3 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {rules.map((r) => (
                        <tr key={r.id} className="hover:bg-slate-50">
                          <td className="py-2.5 px-3 font-mono font-semibold text-slate-900">
                            {r.pattern}
                          </td>
                          <td className="py-2.5 px-3">
                            <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-100 font-mono text-slate-700">
                              {r.match_type}
                            </span>
                          </td>
                          <td className="py-2.5 px-3">
                            <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                              {r.category}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-slate-400 text-[11px]">
                            {r.created_at ? new Date(r.created_at).toLocaleDateString() : '—'}
                          </td>
                          <td className="py-2.5 px-3 text-right">
                            <button
                              onClick={() => handleDeleteRule(r.id)}
                              className="text-rose-500 hover:text-rose-700 p-1 rounded hover:bg-rose-50 transition-colors"
                              title="Delete Rule"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-3 bg-slate-50 border-t border-slate-200 flex justify-end">
              <button
                onClick={() => setShowRulesModal(false)}
                className="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-800 text-xs font-semibold rounded-lg transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
