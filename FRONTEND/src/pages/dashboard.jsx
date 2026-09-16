import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  ScatterChart, Scatter, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import Layout from '../components/Layout';
import * as api from '../services/api';
import { useAuth } from '../context/AuthContext';
import { formatDateTime } from '../utils/datetime';

const KPI_CARDS = [
  { key: 'total_logs', label: 'Total Traffic', color: 'text-slate-800', bg: 'bg-white' },
  { key: 'normal_logs', label: 'Normal', color: 'text-emerald-600', bg: 'bg-emerald-50' },
  { key: 'total_anomalies', label: 'Anomalies', color: 'text-amber-600', bg: 'bg-amber-50' },
  { key: 'anomaly_rate', label: 'Anomaly Rate', color: 'text-rose-600', bg: 'bg-rose-50', suffix: '%' },
];

const PIE_COLORS = { Normal: '#10b981', Anomaly: '#e11d48' };

const RECENT_ANOMALIES_HOURS = 24; // fixed rolling window, no dropdown

export default function DashboardPage() {
  const { user } = useAuth();
  const rangeDays = user?.dashboard_default_range_days || 14;
  const refreshSeconds = user?.dashboard_refresh_interval_seconds || 0;

  const [searchParams] = useSearchParams();
  const uploadId = searchParams.get('upload_id');
  const scope = searchParams.get('scope'); // "combined" | "all" | null (null -> latest upload only)

  // Sent to every dashboard API call so all widgets stay scoped consistently.
  const scopeParams = uploadId ? { upload_id: uploadId } : (scope ? { scope } : {});
  const scopeLabel = uploadId
    ? 'Showing insights for the selected upload only'
    : scope === 'combined'
    ? 'Showing combined insights — uploads still within the 1-month Upload History retention'
    : scope === 'all'
    ? 'Showing all insights currently available'
    : 'Showing insights for the most recent upload only';

  const [summary, setSummary] = useState(null);
  const [trends, setTrends] = useState([]);
  const [recent, setRecent] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [lastRefreshed, setLastRefreshed] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function load(isBackgroundRefresh) {
      if (!isBackgroundRefresh) setLoading(true);
      const [s, t, r] = await Promise.allSettled([
        api.getDashboardSummary(scopeParams),
        api.getAnomalyTrends(rangeDays, scopeParams),
        api.getRecentAnomalies(100, RECENT_ANOMALIES_HOURS, scopeParams),
      ]);
      if (cancelled) return;

      const ok = (res) => (res.status === 'fulfilled' ? res.value.data : null);
      setSummary(ok(s));
      setTrends(ok(t) || []);
      setRecent(ok(r) || []);

      const firstFailure = [s, t, r].find((res) => res.status === 'rejected');
      setError(
        firstFailure
          ? api.getErrorMessage(firstFailure.reason, 'Some dashboard widgets could not load.')
          : ''
      );
      setLastRefreshed(new Date());
      setLoading(false);
    }

    // Runs on mount and whenever the scope/upload_id/recent-window changes —
    // so it also picks up fresh, correctly-scoped data whenever this page is
    // navigated to (e.g. right after a CSV upload completes, or via an
    // Insights link), without needing a manual browser refresh.
    load(false);

    // Dashboard Preferences > refresh interval (Settings page). 0 means off.
    let intervalId = null;
    if (refreshSeconds > 0) {
      intervalId = setInterval(() => load(true), refreshSeconds * 1000);
    }
    return () => { cancelled = true; if (intervalId) clearInterval(intervalId); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rangeDays, refreshSeconds, uploadId, scope]);

  const normalVsAnomaly = summary
    ? [
        { name: 'Normal', value: summary.normal_logs },
        { name: 'Anomaly', value: summary.total_anomalies },
      ]
    : [];
  const hasPieData = normalVsAnomaly.some((d) => d.value > 0);

  return (
    <Layout title="AI DRIVEN NETWORK TRAFFIC ANOMALY DETECTION">
      <div className="mb-4 px-3 py-2 rounded-lg bg-sky-50 border border-sky-200 text-sky-700 text-xs font-semibold">
        {scopeLabel}
      </div>
      {error && (
        <div className="mb-4 p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-sm">{error}</div>
      )}
      {loading ? (
        <div className="text-slate-500 text-sm">Loading dashboard...</div>
      ) : (
        <div className="space-y-6">
          {/* KPI section enclosed in a parent card with a centered title */}
          <div className="p-4 rounded-xl border border-slate-200 bg-white">
            <p className="text-sm font-bold text-slate-700 mb-3 text-center">Network Traffic KPI</p>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {KPI_CARDS.map(({ key, label, color, bg, suffix }) => (
                <div key={key} className={`p-4 rounded-xl border border-slate-200 ${bg}`}>
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{label}</p>
                  <p className={`text-2xl font-extrabold mt-1 ${color}`}>
                    {summary?.[key] ?? 0}{suffix || ''}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* ONE main graph: traffic volume over time, normal vs anomaly */}
          <div className="p-4 rounded-xl border border-slate-200 bg-white">
            <div className="text-center mb-3">
              <p className="text-sm font-bold text-slate-700">
                Traffic Volume Over Time — Normal vs Anomaly
              </p>
              {lastRefreshed && (
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Updated {formatDateTime(lastRefreshed, user?.timezone)}
                  {refreshSeconds > 0 && ` · auto-refreshing every ${refreshSeconds}s`}
                </p>
              )}
            </div>
            {trends.length === 0 ? (
              <p className="text-slate-400 text-sm py-10 text-center">No traffic data yet — upload a dataset to see the trend.</p>
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <ScatterChart>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="date" type="category" allowDuplicatedCategory={false} tick={{ fontSize: 11 }} label={{ value: 'Time', position: 'insideBottom', offset: -4, fontSize: 11, fill: '#94a3b8' }} />
                  <YAxis dataKey="value" tick={{ fontSize: 11 }} allowDecimals={false} label={{ value: 'Traffic Volume', angle: -90, position: 'insideLeft', fontSize: 11, fill: '#94a3b8' }} />
                  <Tooltip cursor={{ strokeDasharray: '3 3' }} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Scatter name="Normal Traffic" data={trends.map((t) => ({ date: t.date, value: t.normal }))} fill="#10b981" />
                  <Scatter name="Anomaly" data={trends.map((t) => ({ date: t.date, value: t.anomalies }))} fill="#e11d48" />
                </ScatterChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* ONE pie chart + existing relevant anomaly information */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="p-4 rounded-xl border border-slate-200 bg-white">
              <p className="text-sm font-bold text-slate-700 mb-3 text-center">Normal vs Anomalous Traffic</p>
              {!hasPieData ? (
                <p className="text-slate-400 text-sm py-10 text-center">No traffic data yet.</p>
              ) : (
                <ResponsiveContainer width="100%" height={240}>
                  <PieChart>
                    <Pie data={normalVsAnomaly} dataKey="value" nameKey="name" innerRadius={50} outerRadius={90} paddingAngle={2}>
                      {normalVsAnomaly.map((d) => <Cell key={d.name} fill={PIE_COLORS[d.name]} />)}
                    </Pie>
                    <Tooltip />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </div>

            {/* Existing relevant anomaly information */}
            <div className="p-4 rounded-xl border border-slate-200 bg-white overflow-x-auto max-h-[420px] overflow-y-auto">
              <div className="flex items-center justify-between mb-3">
                <p className="text-sm font-bold text-slate-700">Recent Anomalies (within 24 hours)</p>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-slate-500 border-b border-slate-200">
                    <th className="py-2 pr-3 font-semibold">Time</th>
                    <th className="py-2 pr-3 font-semibold">Src IP</th>
                    <th className="py-2 pr-3 font-semibold">Severity</th>
                  </tr>
                </thead>
                <tbody>
                  {recent.length === 0 && (
                    <tr><td colSpan={3} className="py-4 text-slate-400 text-center">No recent anomalies</td></tr>
                  )}
                  {recent.map((a) => (
                    <tr key={a.id} className="border-b border-slate-100 hover:bg-slate-50">
                      <td className="py-2 pr-3 text-slate-600 whitespace-nowrap">{formatDateTime(a.time, user?.timezone)}</td>
                      <td className="py-2 pr-3 text-slate-600">{a.src_ip || '—'}</td>
                      <td className="py-2 pr-3">
                        <span className={`px-2 py-0.5 rounded-full text-[11px] font-bold ${
                          a.severity === 'CRITICAL' ? 'bg-rose-100 text-rose-700' :
                          a.severity === 'HIGH' ? 'bg-orange-100 text-orange-700' :
                          a.severity === 'MEDIUM' ? 'bg-amber-100 text-amber-700' :
                          'bg-slate-100 text-slate-600'
                        }`}>{a.severity}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}