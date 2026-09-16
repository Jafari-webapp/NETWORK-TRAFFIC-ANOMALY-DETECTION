import React, { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { UploadCloud, FileWarning, CheckCircle2, Trash2, History, ArrowRight, Eye, Layers, Globe } from 'lucide-react';
import Layout from '../components/Layout';
import * as api from '../services/api';
import { useAuth } from '../context/AuthContext';
import { formatDateTime } from '../utils/datetime';

function StatusBadge({ status }) {
  const styles = {
    success: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    partial: 'bg-amber-50 text-amber-700 border-amber-200',
    error: 'bg-rose-50 text-rose-700 border-rose-200',
  };
  const label = { success: 'Completed', partial: 'Partial', error: 'Failed' }[status] || status;
  return (
    <span className={`px-2 py-0.5 rounded-full text-[11px] font-bold border ${styles[status] || 'bg-slate-50 text-slate-600 border-slate-200'}`}>
      {label}
    </span>
  );
}

export default function UploadPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState('');
  const [clearing, setClearing] = useState(false);
  const inputRef = useRef(null);

  const loadHistory = async () => {
    try {
      const res = await api.getUploadHistory();
      setHistory(res.data);
      setHistoryError('');
    } catch (err) {
      setHistoryError(api.getErrorMessage(err, 'Could not load upload history.'));
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => { loadHistory(); }, []);

  const handleFile = async (file) => {
    if (!file) return;
    setUploading(true);
    setError('');
    setResult(null);
    try {
      const res = await api.uploadLogs(file);
      setResult(res.data);
      loadHistory();
      // Auto-refresh straight to THIS upload's own Dashboard view — give the
      // engineer a moment to see the summary numbers first, then navigate.
      if (res.data.inserted_rows > 0 && res.data.upload_history_id) {
        setTimeout(() => navigate(`/dashboard?upload_id=${res.data.upload_history_id}`), 1500);
      }
    } catch (err) {
      setError(api.getErrorMessage(err, 'Upload failed. Check the file and try again.'));
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  };

  const handleDeleteEntry = async (id) => {
    try {
      await api.deleteUploadHistoryEntry(id);
      setHistory((h) => h.filter((item) => item.id !== id));
    } catch (err) {
      setHistoryError(api.getErrorMessage(err, 'Could not delete this entry.'));
    }
  };

  const handleClearAll = async () => {
    setClearing(true);
    try {
      await api.clearUploadHistory();
      setHistory([]);
    } catch (err) {
      setHistoryError(api.getErrorMessage(err, 'Could not clear upload history.'));
    } finally {
      setClearing(false);
    }
  };

  return (
    <Layout title="Upload Dataset">
      <div className="max-w-4xl">
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            handleFile(e.dataTransfer.files?.[0]);
          }}
          onClick={() => inputRef.current?.click()}
          className={`cursor-pointer rounded-2xl border-2 border-dashed p-10 text-center transition-colors ${
            dragOver ? 'border-sky-500 bg-sky-50' : 'border-slate-300 bg-white hover:border-slate-400'
          }`}
        >
          <UploadCloud className="w-10 h-10 mx-auto text-slate-400 mb-3" />
          <p className="font-semibold text-slate-700">Drag &amp; drop your network/Sophos log dataset here</p>
          <p className="text-sm text-slate-500 mt-1">or click to choose a file — CSV, XLSX, XLS supported</p>
          <p className="text-xs text-slate-400 mt-2">
            This uploads a dataset for analysis — it does not monitor your firewall live.
          </p>
          <input
            ref={inputRef}
            type="file"
            accept=".csv,.xlsx,.xls"
            className="hidden"
            onChange={(e) => handleFile(e.target.files?.[0])}
          />
        </div>

        {uploading && (
          <p className="mt-4 text-sm text-slate-500 flex items-center gap-2">
            <span className="w-3.5 h-3.5 rounded-full border-2 border-sky-500 border-t-transparent animate-spin" />
            Validating dataset, processing, and running anomaly detection...
          </p>
        )}

        {error && (
          <div className="mt-4 p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-sm flex items-start gap-2">
            <FileWarning className="w-4 h-4 mt-0.5 shrink-0" /> {error}
          </div>
        )}

        {result && (
          <div className="mt-4 p-4 rounded-xl border border-slate-200 bg-white">
            <div className="flex items-center gap-2 mb-3">
              {result.status === 'success' ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              ) : (
                <FileWarning className="w-5 h-5 text-amber-500" />
              )}
              <p className="font-bold text-slate-800">{result.filename}</p>
            </div>

            {result.inserted_rows > 0 && (
              <Link
                to={`/dashboard?upload_id=${result.upload_history_id}`}
                className="inline-flex items-center gap-1.5 text-xs font-semibold text-sky-600 hover:text-sky-700 mb-3"
              >
                View updated Dashboard <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            )}

            {result.message && (
              <p className={`text-sm mb-3 ${result.status === 'error' ? 'text-rose-700' : 'text-slate-600'}`}>
                {result.message}
              </p>
            )}

            <div className="grid grid-cols-4 gap-3 text-center text-sm">
              <div className="p-2 rounded-lg bg-slate-50">
                <p className="text-slate-500 text-xs">Total</p>
                <p className="font-bold text-slate-800">{result.total_rows}</p>
              </div>
              <div className="p-2 rounded-lg bg-emerald-50">
                <p className="text-emerald-700 text-xs">Valid</p>
                <p className="font-bold text-emerald-700">{result.valid_rows}</p>
              </div>
              <div className="p-2 rounded-lg bg-rose-50">
                <p className="text-rose-700 text-xs">Invalid</p>
                <p className="font-bold text-rose-700">{result.invalid_rows}</p>
              </div>
              <div className="p-2 rounded-lg bg-sky-50">
                <p className="text-sky-700 text-xs">Inserted</p>
                <p className="font-bold text-sky-700">{result.inserted_rows}</p>
              </div>
            </div>

            {result.missing_columns?.length > 0 && (
              <details className="mt-3 text-xs text-slate-500">
                <summary className="cursor-pointer font-semibold text-rose-700">
                  Missing {result.missing_columns.length} required column(s) — click to view
                </summary>
                <p className="mt-1">{result.missing_columns.join(', ')}</p>
              </details>
            )}

            {result.rejected_row_errors?.length > 0 && (
              <div className="mt-3">
                <p className="text-xs font-semibold text-slate-500 mb-1">Rejected rows (first {result.rejected_row_errors.length}):</p>
                <ul className="text-xs text-slate-500 max-h-32 overflow-y-auto space-y-0.5">
                  {result.rejected_row_errors.map((e, i) => (
                    <li key={i}>Row {e.row}: {e.error}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Upload History — kept for 1 calendar month (time-based only, never record-count limited) */}
        <div className="mt-8 p-4 rounded-xl border border-slate-200 bg-white overflow-x-auto">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm font-bold text-slate-700 flex items-center gap-2">
              <History className="w-4 h-4 text-slate-400" /> Upload History
              <span className="text-xs font-normal text-slate-400">({history.length})</span>
            </p>
            {history.length > 0 && (
              <button
                onClick={handleClearAll}
                disabled={clearing}
                className="text-xs font-semibold text-rose-600 hover:text-rose-700 disabled:opacity-50"
              >
                {clearing ? 'Clearing...' : 'Clear All'}
              </button>
            )}
          </div>

          {historyError && <p className="text-sm text-rose-600 mb-2">{historyError}</p>}

          {historyLoading ? (
            <p className="text-sm text-slate-400">Loading history...</p>
          ) : history.length === 0 ? (
            <p className="text-sm text-slate-400">No uploads yet.</p>
          ) : (
            <table className="w-full min-w-[760px] text-sm">
              <thead>
                <tr className="text-left text-slate-500 border-b border-slate-200">
                  <th className="py-2 pr-3 font-semibold">File Name</th>
                  <th className="py-2 pr-3 font-semibold">Uploaded At</th>
                  <th className="py-2 pr-3 font-semibold">Records</th>
                  <th className="py-2 pr-3 font-semibold">Status</th>
                  <th className="py-2 pr-3 font-semibold">Insights</th>
                  <th className="py-2 pr-3 font-semibold text-right">Delete</th>
                </tr>
              </thead>
              <tbody>
                {history.map((h) => (
                  <tr key={h.id} className="border-b border-slate-100">
                    <td className="py-2 pr-3 text-slate-700 font-medium">{h.filename}</td>
                    <td className="py-2 pr-3 text-slate-500">{formatDateTime(h.uploaded_at, user?.timezone)}</td>
                    <td className="py-2 pr-3 text-slate-500">{h.inserted_rows}/{h.total_rows}</td>
                    <td className="py-2 pr-3"><StatusBadge status={h.status} /></td>
                    <td className="py-2 pr-3">
                      <div className="flex items-center gap-2.5 whitespace-nowrap">
                        <Link
                          to={`/dashboard?upload_id=${h.id}`}
                          title="Dashboard for this upload only"
                          className="inline-flex items-center gap-1 text-[11px] font-semibold text-sky-600 hover:text-sky-700"
                        >
                          <Eye className="w-3.5 h-3.5" /> View
                        </Link>
                        <Link
                          to="/dashboard?scope=combined"
                          title="Dashboard combining all uploads still within retention"
                          className="inline-flex items-center gap-1 text-[11px] font-semibold text-indigo-600 hover:text-indigo-700"
                        >
                          <Layers className="w-3.5 h-3.5" /> Combined
                        </Link>
                        <Link
                          to="/dashboard?scope=all"
                          title="Dashboard for all currently available data"
                          className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-600 hover:text-emerald-700"
                        >
                          <Globe className="w-3.5 h-3.5" /> All
                        </Link>
                      </div>
                    </td>
                    <td className="py-2 pr-3 text-right">
                      <button
                        onClick={() => handleDeleteEntry(h.id)}
                        className="text-slate-400 hover:text-rose-600 transition-colors"
                        aria-label="Delete upload record"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </Layout>
  );
}
