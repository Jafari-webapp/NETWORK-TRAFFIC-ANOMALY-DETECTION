import React, { useState } from 'react';
import { FileText, BarChart3, Download } from 'lucide-react';
import jsPDF from 'jspdf';
import Layout from '../components/Layout';
import MarkdownLite from '../components/MarkdownLite';
import * as api from '../services/api';
import { useAuth } from '../context/AuthContext';
import { formatDateTime } from '../utils/datetime';

const PERIODS = [
  { value: 'today', label: 'Today' },
  { value: 'weekly', label: 'This Week' },
  { value: 'monthly', label: 'This Month' },
  { value: 'all', label: 'All Time' },
];

const REPORT_TYPES = [
  { value: 'executive_summary', label: 'Executive Summary' },
  { value: 'incident_report', label: 'Incident Report' },
  { value: 'threat_overview', label: 'Threat Overview' },
];

export default function ReportsPage() {
  const { user } = useAuth();
  const [period, setPeriod] = useState('today');
  const [reportType, setReportType] = useState('executive_summary');
  const [generating, setGenerating] = useState(false);
  const [report, setReport] = useState(null);
  const [rejected, setRejected] = useState('');
  const [error, setError] = useState('');

  const handleGenerate = async () => {
    setGenerating(true);
    setError('');
    setRejected('');
    setReport(null);
    try {
      const res = await api.generateReport(period, reportType);
      if (res.data.allowed) {
        setReport(res.data);
      } else {
        // Not a technical error — a clear, expected business rule (e.g. the
        // week/month hasn't ended yet, or there's no data for this period).
        setRejected(res.data.message || 'This report cannot be generated right now.');
      }
    } catch (err) {
      setError(api.getErrorMessage(err, 'Report generation failed.'));
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = () => {
    if (!report) return;
    const typeLabel = REPORT_TYPES.find((r) => r.value === report.report_type)?.label || report.report_type;
    const periodLabel = PERIODS.find((p) => p.value === report.period)?.label || report.period;
    const generatedLabel = formatDateTime(report.generated_at, user?.timezone);

    const doc = new jsPDF({ unit: 'pt', format: 'a4' });
    const pageWidth = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();
    const margin = 48;
    const maxWidth = pageWidth - margin * 2;
    let y = margin;

    const addPageIfNeeded = (lineHeight) => {
      if (y + lineHeight > pageHeight - margin) {
        doc.addPage();
        y = margin;
      }
    };

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(16);
    doc.splitTextToSize(`${typeLabel} — ${periodLabel}`, maxWidth).forEach((line) => {
      addPageIfNeeded(20);
      doc.text(line, margin, y);
      y += 20;
    });

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(9);
    doc.setTextColor(120);
    addPageIfNeeded(14);
    doc.text(`Generated at ${generatedLabel}`, margin, y);
    y += 24;
    doc.setTextColor(20);

    // Render the Gemini report text as clean PDF body copy (strip raw
    // markdown syntax, keep headings bold and bullets as bullets).
    report.report_text.split('\n').forEach((rawLine) => {
      let line = rawLine.trim();
      let isHeading = false;
      if (/^#{1,6}\s+/.test(line)) {
        isHeading = true;
        line = line.replace(/^#{1,6}\s+/, '');
      }
      line = line.replace(/\*\*(.*?)\*\*/g, '$1').replace(/\*(.*?)\*/g, '$1');
      if (/^[-*]\s+/.test(line)) {
        line = '•  ' + line.replace(/^[-*]\s+/, '');
      }

      if (line === '') {
        y += 8;
        return;
      }

      doc.setFont('helvetica', isHeading ? 'bold' : 'normal');
      doc.setFontSize(isHeading ? 12 : 10.5);
      const lineHeight = isHeading ? 18 : 14;

      doc.splitTextToSize(line, maxWidth).forEach((wrapped) => {
        addPageIfNeeded(lineHeight);
        doc.text(wrapped, margin, y);
        y += lineHeight;
      });
    });

    const filename = `${report.report_type}_${report.period}_${new Date(report.generated_at).toISOString().slice(0, 10)}.pdf`;
    doc.save(filename);
  };

  return (
    <Layout title="Report Generator">
      <div className="max-w-3xl space-y-5">
        <div className="p-5 rounded-xl border border-slate-200 bg-white">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-xs font-semibold text-slate-500 mb-1.5">Period</label>
              <select
                value={period}
                onChange={(e) => setPeriod(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-emerald-500/30"
              >
                {PERIODS.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 mb-1.5">Report Type</label>
              <select
                value={reportType}
                onChange={(e) => setReportType(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-emerald-500/30"
              >
                {REPORT_TYPES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
              </select>
            </div>
          </div>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-sky-600 text-white text-sm font-semibold hover:bg-sky-700 disabled:opacity-50"
          >
            <BarChart3 className="w-4 h-4" />
            {generating ? 'Generating...' : 'Generate Standard Report'}
          </button>
        </div>

        {error && <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-sm">{error}</div>}
        {rejected && <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-sm">{rejected}</div>}

        {report && (
          <div className="p-5 rounded-xl border border-slate-200 bg-white">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2 text-slate-700">
                <FileText className="w-4 h-4" />
                <p className="font-bold text-sm">
                  {REPORT_TYPES.find((r) => r.value === report.report_type)?.label} — {PERIODS.find((p) => p.value === report.period)?.label}
                </p>
              </div>
              <button
                onClick={handleDownload}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 text-slate-700 text-xs font-semibold hover:bg-slate-50"
              >
                <Download className="w-3.5 h-3.5" />
                Download Report
              </button>
            </div>
            <p className="text-xs text-slate-400 mb-4">Generated at {formatDateTime(report.generated_at, user?.timezone)}</p>
            <div className="text-sm text-slate-700 leading-relaxed">
              <MarkdownLite text={report.report_text} />
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}
