import React, { useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight, Search } from 'lucide-react';
import Layout from '../components/Layout';
import * as api from '../services/api';
import { useAuth } from '../context/AuthContext';
import { formatDateTime } from '../utils/datetime';

export default function LogsPage() {
  const { user } = useAuth();
  const [logs, setLogs] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [filters, setFilters] = useState({ protocol: '', src_ip: '', dst_ip: '' });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = async (pageArg = page) => {
    setLoading(true);
    setError('');
    try {
      const params = { page: pageArg, page_size: 20 };
      if (filters.protocol) params.protocol = filters.protocol;
      if (filters.src_ip) params.src_ip = filters.src_ip;
      if (filters.dst_ip) params.dst_ip = filters.dst_ip;
      const res = await api.getLogs(params);
      setLogs(res.data.items);
      setTotalPages(res.data.total_pages);
      setTotal(res.data.total);
      setPage(pageArg);
    } catch (err) {
      setError(api.getErrorMessage(err, 'Could not load logs.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(1); /* eslint-disable-next-line */ }, []);

  return (
    <Layout title="Firewall Logs">
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <div>
          <label className="block text-xs font-semibold text-slate-500 mb-1">Protocol</label>
          <input
            value={filters.protocol}
            onChange={(e) => setFilters({ ...filters, protocol: e.target.value })}
            placeholder="TCP / UDP"
            className="px-3 py-1.5 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-emerald-500/30"
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-500 mb-1">Source IP</label>
          <input
            value={filters.src_ip}
            onChange={(e) => setFilters({ ...filters, src_ip: e.target.value })}
            className="px-3 py-1.5 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-emerald-500/30"
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-500 mb-1">Destination IP</label>
          <input
            value={filters.dst_ip}
            onChange={(e) => setFilters({ ...filters, dst_ip: e.target.value })}
            className="px-3 py-1.5 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-emerald-500/30"
          />
        </div>
        <button
          onClick={() => load(1)}
          className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-sky-600 text-white text-sm font-medium hover:bg-sky-700"
        >
          <Search className="w-3.5 h-3.5" /> Filter
        </button>
        <span className="text-sm text-slate-500 ml-auto">{total} total logs</span>
      </div>

      {error && <div className="mb-4 p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-sm">{error}</div>}

      <div className="rounded-xl border border-slate-200 bg-white overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-500 border-b border-slate-200 bg-slate-50">
              <th className="py-2.5 px-3 font-semibold">Time</th>
              <th className="py-2.5 px-3 font-semibold">Src IP</th>
              <th className="py-2.5 px-3 font-semibold">Dst IP</th>
              <th className="py-2.5 px-3 font-semibold">Protocol</th>
              <th className="py-2.5 px-3 font-semibold">Src Port</th>
              <th className="py-2.5 px-3 font-semibold">Dst Port</th>
              <th className="py-2.5 px-3 font-semibold">Rule</th>
              <th className="py-2.5 px-3 font-semibold">Message</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={8} className="py-6 text-center text-slate-400">Loading...</td></tr>
            ) : logs.length === 0 ? (
              <tr><td colSpan={8} className="py-6 text-center text-slate-400">No logs found.</td></tr>
            ) : (
              logs.map((log) => (
                <tr key={log.id} className="border-b border-slate-100 hover:bg-slate-50">
                  <td className="py-2 px-3 text-slate-600 whitespace-nowrap">{formatDateTime(log.time, user?.timezone)}</td>
                  <td className="py-2 px-3 text-slate-600">{log.src_ip || '—'}</td>
                  <td className="py-2 px-3 text-slate-600">{log.dst_ip || '—'}</td>
                  <td className="py-2 px-3 text-slate-600">{log.protocol || '—'}</td>
                  <td className="py-2 px-3 text-slate-600">{log.src_port ?? '—'}</td>
                  <td className="py-2 px-3 text-slate-600">{log.dst_port ?? '—'}</td>
                  <td className="py-2 px-3 text-slate-600">{log.firewall_rule_name || log.firewall_rule || '—'}</td>
                  <td className="py-2 px-3 text-slate-500 max-w-xs truncate">{log.message || '—'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-4 flex items-center justify-between text-sm">
        <span className="text-slate-500">Page {page} of {totalPages}</span>
        <div className="flex gap-2">
          <button
            disabled={page <= 1}
            onClick={() => load(page - 1)}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-300 disabled:opacity-40 hover:bg-slate-50"
          >
            <ChevronLeft className="w-4 h-4" /> Prev
          </button>
          <button
            disabled={page >= totalPages}
            onClick={() => load(page + 1)}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-300 disabled:opacity-40 hover:bg-slate-50"
          >
            Next <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </Layout>
  );
}
