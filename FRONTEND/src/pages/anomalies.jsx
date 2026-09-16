import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Layout from '../components/Layout';
import * as api from '../services/api';
import { useAuth } from '../context/AuthContext';
import { formatDateTime } from '../utils/datetime';

const SEVERITY_STYLE = {
  CRITICAL: 'bg-rose-100 text-rose-700',
  HIGH: 'bg-orange-100 text-orange-700',
  MEDIUM: 'bg-amber-100 text-amber-700',
  LOW: 'bg-slate-100 text-slate-600',
};

export default function AnomaliesPage() {
  const { user } = useAuth();
  const [anomalies, setAnomalies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    api.getRecentAnomalies(100, 0)
      .then((res) => setAnomalies(res.data))
      .catch((err) => setError(api.getErrorMessage(err, 'Could not load anomalies.')))
      .finally(() => setLoading(false));
  }, []);

  return (
    <Layout title="Anomalies">
      {error && <div className="mb-4 p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-sm">{error}</div>}
      <div className="rounded-xl border border-slate-200 bg-white overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-500 border-b border-slate-200 bg-slate-50">
              <th className="py-2.5 px-3 font-semibold">Time</th>
              <th className="py-2.5 px-3 font-semibold">Src IP</th>
              <th className="py-2.5 px-3 font-semibold">Dst IP : Port</th>
              <th className="py-2.5 px-3 font-semibold">Protocol</th>
              <th className="py-2.5 px-3 font-semibold">Score</th>
              <th className="py-2.5 px-3 font-semibold">Confidence</th>
              <th className="py-2.5 px-3 font-semibold">Severity</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} className="py-6 text-center text-slate-400">Loading...</td></tr>
            ) : anomalies.length === 0 ? (
              <tr><td colSpan={7} className="py-6 text-center text-slate-400">No anomalies detected yet.</td></tr>
            ) : (
              anomalies.map((a) => (
                <tr
                  key={a.id}
                  onClick={() => navigate(`/anomalies/${a.id}`)}
                  className="border-b border-slate-100 hover:bg-slate-50 cursor-pointer"
                >
                  <td className="py-2 px-3 text-slate-600 whitespace-nowrap">{formatDateTime(a.time, user?.timezone)}</td>
                  <td className="py-2 px-3 text-slate-600">{a.src_ip || '—'}</td>
                  <td className="py-2 px-3 text-slate-600">{a.dst_ip || '—'}:{a.dst_port ?? '—'}</td>
                  <td className="py-2 px-3 text-slate-600">{a.protocol || '—'}</td>
                  <td className="py-2 px-3 text-slate-600">{a.anomaly_score.toFixed(4)}</td>
                  <td className="py-2 px-3 text-slate-600">{a.confidence != null ? `${Math.round(a.confidence * 100)}%` : '—'}</td>
                  <td className="py-2 px-3">
                    <span className={`px-2 py-0.5 rounded-full text-[11px] font-bold ${SEVERITY_STYLE[a.severity] || 'bg-slate-100 text-slate-600'}`}>
                      {a.severity}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </Layout>
  );
}
