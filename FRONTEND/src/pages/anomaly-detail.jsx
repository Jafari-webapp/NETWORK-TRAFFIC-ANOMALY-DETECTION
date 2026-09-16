import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Sparkles } from 'lucide-react';
import Layout from '../components/Layout';
import * as api from '../services/api';
import { useAuth } from '../context/AuthContext';
import { formatDateTime } from '../utils/datetime';

function Field({ label, value }) {
  return (
    <div>
      <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide">{label}</p>
      <p className="text-sm text-slate-800 font-medium">{value ?? '—'}</p>
    </div>
  );
}

export default function AnomalyDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeError, setAnalyzeError] = useState('');

  const load = () => {
    setLoading(true);
    api.getAnomalyDetail(id)
      .then((res) => setData(res.data))
      .catch((err) => setError(api.getErrorMessage(err, 'Could not load this anomaly.')))
      .finally(() => setLoading(false));
  };

  useEffect(load, [id]);

  const handleAnalyze = async () => {
    setAnalyzing(true);
    setAnalyzeError('');
    try {
      await api.analyzeWithGemini(id);
      load();
    } catch (err) {
      setAnalyzeError(err?.response?.data?.detail || 'Gemini analysis failed. Check GEMINI_API_KEY in backend .env.');
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <Layout title={`Anomaly #${id}`}>
      <button onClick={() => navigate('/anomalies')} className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800 mb-4">
        <ArrowLeft className="w-4 h-4" /> Back to Anomalies
      </button>

      {loading && <p className="text-slate-500 text-sm">Loading...</p>}
      {error && <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-sm">{error}</div>}

      {data && (
        <div className="space-y-5 max-w-4xl">
          <div className="p-5 rounded-xl border border-slate-200 bg-white">
            <p className="text-sm font-bold text-slate-700 mb-3">Network Information</p>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <Field label="Source IP" value={data.firewall_log.src_ip} />
              <Field label="Destination IP" value={data.firewall_log.dst_ip} />
              <Field label="Source Port" value={data.firewall_log.src_port} />
              <Field label="Destination Port" value={data.firewall_log.dst_port} />
              <Field label="Protocol" value={data.firewall_log.protocol} />
              <Field label="Username" value={data.firewall_log.username} />
              <Field label="Firewall Rule" value={data.firewall_log.firewall_rule_name || data.firewall_log.firewall_rule} />
              <Field label="NAT Rule" value={data.firewall_log.nat_rule_name || data.firewall_log.nat_rule} />
              <Field label="In Interface" value={data.firewall_log.in_interface} />
              <Field label="Out Interface" value={data.firewall_log.out_interface} />
            </div>
          </div>

          <div className="p-5 rounded-xl border border-slate-200 bg-white">
            <p className="text-sm font-bold text-slate-700 mb-3">Detection</p>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <Field label="Is Anomaly" value={data.is_anomaly ? 'Yes' : 'No'} />
              <Field label="Anomaly Score" value={data.anomaly_score.toFixed(4)} />
              <Field label="Severity" value={data.severity} />
              <Field label="Confidence" value={data.confidence != null ? `${Math.round(data.confidence * 100)}%` : '—'} />
              <Field label="Algorithm" value={data.algorithm} />
              <Field label="Detected At" value={formatDateTime(data.detected_at, user?.timezone)} />
            </div>
          </div>

          <div className="p-5 rounded-xl border border-slate-200 bg-white">
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm font-bold text-slate-700 flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-emerald-500" /> Gemini AI Analysis
              </p>
              {!data.llm_analysis && (
                <button
                  onClick={handleAnalyze}
                  disabled={analyzing}
                  className="px-3.5 py-1.5 rounded-lg bg-sky-600 text-white text-xs font-semibold hover:bg-sky-700 disabled:opacity-50"
                >
                  {analyzing ? 'Analyzing...' : 'Analyze with AI'}
                </button>
              )}
            </div>

            {analyzeError && (
              <div className="mb-3 p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs">{analyzeError}</div>
            )}

            {data.llm_analysis ? (
              <div className="space-y-3 text-sm">
                <div>
                  <p className="text-[11px] font-semibold text-slate-400 uppercase">Analysis</p>
                  <p className="text-slate-700">{data.llm_analysis.analysis}</p>
                </div>
                <div>
                  <p className="text-[11px] font-semibold text-slate-400 uppercase">Possible Cause</p>
                  <p className="text-slate-700">{data.llm_analysis.possible_cause}</p>
                </div>
                <div>
                  <p className="text-[11px] font-semibold text-slate-400 uppercase">Risk</p>
                  <p className="text-slate-700">{data.llm_analysis.risk_explanation}</p>
                </div>
                <div>
                  <p className="text-[11px] font-semibold text-slate-400 uppercase">Recommendation</p>
                  <p className="text-slate-700">{data.llm_analysis.recommendation}</p>
                </div>
              </div>
            ) : (
              <p className="text-slate-400 text-sm">No AI analysis yet — click "Analyze with AI" to generate one.</p>
            )}
          </div>
        </div>
      )}
    </Layout>
  );
}


