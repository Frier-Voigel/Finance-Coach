import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  UploadCloud,
  FileText,
  MessageSquare,
  CheckCircle,
  AlertTriangle,
  ArrowRight,
  Database,
  RefreshCw,
  FileCheck,
} from 'lucide-react';
import { api } from '../../api/client';
import { useToast } from '../../components/Toast';

const SAMPLE_CSV = `Date,Description,Debit,Credit,Balance
01/04/2025,UPI-SWIGGY-12345,450.00,,45200.00
05/04/2025,ECOM NETFLIX DIGITAL,649.00,,44551.00
07/04/2025,ECOM SPOTIFY MUSIC,119.00,,44432.00
10/04/2025,SALARY ACME TECHNOLOGIES,,60000.00,104432.00
12/04/2025,UPI-UBER INDIA-9821,320.00,,104112.00
15/04/2025,NEFT RENT LANDLORD RAJESH,18000.00,,86112.00
18/04/2025,UPI-SWIGGY-54321,580.00,,85532.00
22/04/2025,POS DMART SUPERMARKET,3240.00,,82292.00`;

const SAMPLE_SMS = `Rs.450.00 debited from A/c XX1234 at SWIGGY on 12-Apr. Bal: Rs.45,200.00.
Rs.649.00 debited from A/c XX1234 at NETFLIX on 05-May.
Rs.119.00 debited from A/c XX1234 at SPOTIFY on 07-May.
Rs.60,000.00 credited to A/c XX1234 by ACME TECHNOLOGIES on 30-Apr.
Rs.280.00 debited from A/c XX1234 at UBER INDIA on 14-May.
Rs.850.00 debited from A/c XX1234 at ZOMATO on 18-May.`;

export default function UploadPage() {
  const navigate = useNavigate();
  const { addToast } = useToast();

  const [activeTab, setActiveTab] = useState('statement'); // 'statement' | 'sms'
  const [file, setFile] = useState(null);
  const [account, setAccount] = useState('HDFC-Main-1234');
  const [smsText, setSmsText] = useState('');
  const [smsYear, setSmsYear] = useState(2025);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleFileDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
      setError(null);
    }
  };

  const handleLoadSampleCsv = () => {
    const blob = new Blob([SAMPLE_CSV], { type: 'text/csv' });
    const sampleFile = new File([blob], 'sample_bank_statement.csv', { type: 'text/csv' });
    setFile(sampleFile);
    setError(null);
    addToast({
      type: 'info',
      title: 'Sample CSV Attached',
      message: 'Attached a synthetic 8-transaction bank statement CSV.',
    });
  };

  const handleLoadSampleSms = () => {
    setSmsText(SAMPLE_SMS);
    setError(null);
    addToast({
      type: 'info',
      title: 'Sample SMS Loaded',
      message: 'Populated SMS textarea with synthetic bank alerts.',
    });
  };

  const handleUploadFile = async (e) => {
    e.preventDefault();
    if (!file) {
      setError('Please select or drop a CSV or PDF statement file.');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await api.uploadStatement(file, account);
      setResult(res);
      addToast({
        type: 'success',
        title: 'Statement Ingested Successfully',
        message: `Parsed & categorized ${res.inserted || 0} transactions (${res.duplicates_skipped || 0} duplicates skipped).`,
      });
    } catch (err) {
      setError(err.message || 'Failed to upload and parse statement.');
      addToast({
        type: 'error',
        title: 'Upload Failed',
        message: err.message || 'Check file format.',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleIngestSms = async (e) => {
    e.preventDefault();
    if (!smsText.trim()) {
      setError('Please paste at least one bank SMS alert.');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await api.ingestSms(smsText, parseInt(smsYear, 10) || 2025);
      setResult(res);
      addToast({
        type: 'success',
        title: 'SMS Alerts Ingested',
        message: `Parsed ${res.inserted || 0} transactions from SMS.`,
      });
    } catch (err) {
      setError(err.message || 'Failed to ingest SMS alerts.');
      addToast({
        type: 'error',
        title: 'SMS Ingestion Failed',
        message: err.message || 'Could not parse SMS messages.',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Upload Financial Statements</h1>
        <p className="text-sm text-slate-500 mt-1">
          Ingest raw bank statements (CSV, PDF) or paste transaction SMS. Auto-normalizes, deduplicates, and categorizes with rule engine.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex space-x-2 border-b border-slate-200">
        <button
          onClick={() => { setActiveTab('statement'); setError(null); }}
          className={`flex items-center gap-2 pb-3 px-4 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'statement'
              ? 'border-sky-600 text-sky-600'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          <FileText className="w-4 h-4" />
          Bank Statement (CSV / PDF)
        </button>
        <button
          onClick={() => { setActiveTab('sms'); setError(null); }}
          className={`flex items-center gap-2 pb-3 px-4 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'sms'
              ? 'border-sky-600 text-sky-600'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          <MessageSquare className="w-4 h-4" />
          Paste SMS Alerts
        </button>
      </div>

      {error && (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 flex items-center gap-3 text-rose-800 text-sm">
          <AlertTriangle className="w-5 h-5 flex-shrink-0 text-rose-600" />
          <span>{error}</span>
        </div>
      )}

      {/* Tab 1: Statement Upload */}
      {activeTab === 'statement' && (
        <div className="bg-white rounded-2xl shadow-xs border border-slate-200 p-6 space-y-6">
          <form onSubmit={handleUploadFile} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="md:col-span-2">
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
                  Account Name / Tag (Optional)
                </label>
                <input
                  type="text"
                  value={account}
                  onChange={(e) => setAccount(e.target.value)}
                  placeholder="e.g. HDFC-Salary-1234, SBI-Card"
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 focus:bg-white transition-all"
                />
              </div>

              <div className="flex flex-col justify-end">
                <button
                  type="button"
                  onClick={handleLoadSampleCsv}
                  className="w-full flex items-center justify-center gap-1.5 px-3 py-2.5 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg border border-slate-300 transition-colors"
                >
                  <Database className="w-3.5 h-3.5 text-sky-600" />
                  Load Sample Synthetic CSV
                </button>
              </div>
            </div>

            {/* Dropzone */}
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleFileDrop}
              className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
                file
                  ? 'border-sky-400 bg-sky-50/50'
                  : 'border-slate-300 hover:border-sky-400 bg-slate-50/50'
              }`}
            >
              <input
                type="file"
                id="file-upload"
                accept=".csv,.pdf,text/csv,application/pdf"
                onChange={handleFileChange}
                className="hidden"
              />
              <label
                htmlFor="file-upload"
                className="cursor-pointer flex flex-col items-center justify-center space-y-2"
              >
                <div className="w-12 h-12 rounded-full bg-sky-100 text-sky-600 flex items-center justify-center">
                  <UploadCloud className="w-6 h-6" />
                </div>
                <div className="text-sm font-medium text-slate-700">
                  {file ? (
                    <span className="text-sky-700 font-semibold">{file.name}</span>
                  ) : (
                    <>Click to select or drag and drop a statement</>
                  )}
                </div>
                <p className="text-xs text-slate-500">
                  Supports CSV (auto-mapped columns) & PDF (pdfplumber table extract)
                </p>
                {file && (
                  <span className="text-xs text-slate-500 bg-white px-2.5 py-1 rounded-full border border-slate-200 mt-1">
                    {(file.size / 1024).toFixed(1)} KB • {file.type || 'statement'}
                  </span>
                )}
              </label>
            </div>

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={loading || !file}
                className="flex items-center gap-2 px-6 py-2.5 bg-sky-600 hover:bg-sky-700 disabled:opacity-50 text-white rounded-lg font-medium text-sm shadow-sm transition-all shadow-sky-600/20"
              >
                {loading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Parsing Statement...
                  </>
                ) : (
                  <>
                    <FileCheck className="w-4 h-4" />
                    Parse & Ingest Statement
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Tab 2: SMS Paste */}
      {activeTab === 'sms' && (
        <div className="bg-white rounded-2xl shadow-xs border border-slate-200 p-6 space-y-6">
          <form onSubmit={handleIngestSms} className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
                  Raw Bank SMS Alerts
                </label>
                <p className="text-xs text-slate-500 mt-0.5">
                  Paste bank debit/credit notification SMS messages (one per line).
                </p>
              </div>
              <button
                type="button"
                onClick={handleLoadSampleSms}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg border border-slate-300 transition-colors"
              >
                <Database className="w-3.5 h-3.5 text-sky-600" />
                Fill Sample SMS
              </button>
            </div>

            <textarea
              rows={6}
              value={smsText}
              onChange={(e) => setSmsText(e.target.value)}
              placeholder="e.g. Rs.450.00 debited from A/c XX1234 at SWIGGY on 12-Apr..."
              className="w-full p-3.5 font-mono text-xs bg-slate-50 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-sky-500 focus:bg-white transition-all leading-relaxed"
            />

            <div className="flex items-center justify-between">
              <div className="w-48">
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Default Year
                </label>
                <input
                  type="number"
                  value={smsYear}
                  onChange={(e) => setSmsYear(e.target.value)}
                  className="w-full px-3 py-1.5 bg-slate-50 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
                />
              </div>

              <button
                type="submit"
                disabled={loading || !smsText.trim()}
                className="flex items-center gap-2 px-6 py-2.5 bg-sky-600 hover:bg-sky-700 disabled:opacity-50 text-white rounded-lg font-medium text-sm shadow-sm transition-all shadow-sky-600/20"
              >
                {loading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Parsing SMS...
                  </>
                ) : (
                  <>
                    <MessageSquare className="w-4 h-4" />
                    Ingest SMS Messages
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Ingestion Results Display */}
      {result && (
        <div className="bg-white rounded-2xl shadow-sm border border-emerald-200 p-6 space-y-6 animate-fadeIn">
          <div className="flex items-center justify-between pb-4 border-b border-slate-100">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center">
                <CheckCircle className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-slate-900">Ingestion Batch Completed</h3>
                <p className="text-xs text-slate-500">
                  Transactions have been normalized and saved to database.
                </p>
              </div>
            </div>

            <button
              onClick={() => navigate('/review')}
              className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-medium rounded-lg shadow-sm transition-colors"
            >
              Review Transactions & Rules
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Stats Bar */}
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-emerald-50/70 border border-emerald-200 rounded-xl p-4 text-center">
              <span className="text-2xl font-bold text-emerald-700">{result.inserted || 0}</span>
              <p className="text-xs font-medium text-emerald-900 mt-0.5">Transactions Inserted</p>
            </div>

            <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 text-center">
              <span className="text-2xl font-bold text-slate-700">{result.duplicates_skipped || 0}</span>
              <p className="text-xs font-medium text-slate-600 mt-0.5">Duplicates Skipped</p>
            </div>

            <div className="bg-amber-50/70 border border-amber-200 rounded-xl p-4 text-center">
              <span className="text-2xl font-bold text-amber-700">
                {result.unparsed ? result.unparsed.length : 0}
              </span>
              <p className="text-xs font-medium text-amber-900 mt-0.5">Unparsed Lines</p>
            </div>
          </div>

          {/* Unparsed lines alert if any */}
          {result.unparsed && result.unparsed.length > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-xs text-amber-900 space-y-1">
              <p className="font-semibold flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                Unparsed lines:
              </p>
              <ul className="list-disc pl-5 font-mono text-[11px] text-amber-800 space-y-0.5 max-h-32 overflow-y-auto">
                {result.unparsed.map((item, idx) => (
                  <li key={idx}>{typeof item === 'string' ? item : item.raw || JSON.stringify(item)}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Table Preview */}
          {result.transactions && result.transactions.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-xs font-semibold text-slate-700 uppercase tracking-wider">
                Preview of Ingested Rows ({result.transactions.length})
              </h4>
              <div className="overflow-x-auto border border-slate-200 rounded-xl">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-600 font-medium border-b border-slate-200">
                    <tr>
                      <th className="py-2.5 px-3">Date</th>
                      <th className="py-2.5 px-3">Merchant</th>
                      <th className="py-2.5 px-3">Description</th>
                      <th className="py-2.5 px-3">Category</th>
                      <th className="py-2.5 px-3">Direction</th>
                      <th className="py-2.5 px-3 text-right">Amount</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {result.transactions.slice(0, 8).map((txn, idx) => (
                      <tr key={idx} className="hover:bg-slate-50">
                        <td className="py-2 px-3 text-slate-600 font-mono">{txn.date}</td>
                        <td className="py-2 px-3 font-semibold text-slate-900">{txn.merchant || '—'}</td>
                        <td className="py-2 px-3 text-slate-500 truncate max-w-xs">{txn.description}</td>
                        <td className="py-2 px-3">
                          <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-sky-50 text-sky-700 border border-sky-200">
                            {txn.category || 'Other'}
                          </span>
                        </td>
                        <td className="py-2 px-3">
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-medium uppercase ${
                              txn.direction === 'debit'
                                ? 'bg-rose-50 text-rose-700'
                                : 'bg-emerald-50 text-emerald-700'
                            }`}
                          >
                            {txn.direction}
                          </span>
                        </td>
                        <td className="py-2 px-3 text-right font-mono font-semibold text-slate-900">
                          {txn.direction === 'debit' ? '-' : '+'}₹{parseFloat(txn.amount).toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {result.transactions.length > 8 && (
                <p className="text-center text-xs text-slate-400">
                  Showing 8 of {result.transactions.length} rows. Open Transactions Review for all.
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
