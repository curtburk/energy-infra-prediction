import { useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import {
  AlertTriangle, CheckCircle, Clock, ChevronDown, ChevronUp,
  Download, Activity, Shield,
} from 'lucide-react';
import type { AnalysisResults, EquipmentResult } from '../types';
import { getVideoUrl } from '../api/client';

interface Props {
  jobId: string;
  results: AnalysisResults;
  onNewAnalysis: () => void;
}

// Color map for equipment types
const TYPE_COLORS: Record<string, string> = {
  transformer: '#3b82f6',
  bushing: '#8b5cf6',
  insulator: '#06b6d4',
  circuit_breaker: '#f59e0b',
  other: '#6b7280',
};

const SEVERITY_STYLES: Record<string, { bg: string; text: string; border: string }> = {
  CRITICAL: { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/30' },
  WARNING: { bg: 'bg-amber-500/10', text: 'text-amber-400', border: 'border-amber-500/30' },
  WATCH: { bg: 'bg-blue-500/10', text: 'text-blue-400', border: 'border-blue-500/30' },
  NORMAL: { bg: 'bg-green-500/10', text: 'text-green-400', border: 'border-green-500/30' },
};

function SeverityBadge({ severity }: { severity: string }) {
  const style = SEVERITY_STYLES[severity] || SEVERITY_STYLES.NORMAL;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border ${style.bg} ${style.text} ${style.border}`}>
      {severity === 'CRITICAL' && <AlertTriangle className="w-3 h-3" />}
      {severity === 'NORMAL' && <CheckCircle className="w-3 h-3" />}
      {severity}
    </span>
  );
}

function HealthBar({ score }: { score: number }) {
  const color = score >= 80 ? 'bg-green-500' : score >= 50 ? 'bg-amber-500' : 'bg-red-500';
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-zinc-400">Health</span>
        <span className="text-white font-mono">{score}/100</span>
      </div>
      <div className="w-full h-2 bg-bg-tertiary rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${score}%` }} />
      </div>
    </div>
  );
}

function EquipmentCard({ result }: { result: EquipmentResult }) {
  const [expanded, setExpanded] = useState(false);
  const anomalies = result.current_state.anomalies_detected;
  const health = result.current_state.overall_health_score;
  const ttf = result.time_to_failure_estimate;

  const worstSeverity = anomalies.length > 0
    ? anomalies.reduce((w, a) => {
        const order = ['CRITICAL', 'WARNING', 'WATCH', 'NORMAL'];
        return order.indexOf(a.severity) < order.indexOf(w) ? a.severity : w;
      }, 'NORMAL' as string)
    : 'NORMAL';

  const typeColor = TYPE_COLORS[result.type] || TYPE_COLORS.other;

  return (
    <div className="bg-bg-secondary border border-bg-tertiary rounded-lg overflow-hidden">
      {/* Header */}
      <div className="p-4 flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: typeColor }} />
          <div>
            <h3 className="font-semibold text-white">{result.label}</h3>
            <p className="text-xs text-zinc-500 capitalize">{result.type.replace('_', ' ')}</p>
          </div>
        </div>
        {ttf && (
          <div className={`px-3 py-1 rounded-full text-xs font-mono font-medium ${
            SEVERITY_STYLES[worstSeverity]?.bg || ''
          } ${SEVERITY_STYLES[worstSeverity]?.text || ''}`}>
            <Clock className="w-3 h-3 inline mr-1" />
            TTF: {ttf.days}d
          </div>
        )}
      </div>

      {/* Body */}
      <div className="px-4 pb-4 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <HealthBar score={health} />
          <div>
            <p className="text-xs text-zinc-400 mb-1">Anomalies</p>
            {anomalies.length > 0 ? (
              <div className="flex flex-wrap gap-1">
                {anomalies.map((a, i) => (
                  <SeverityBadge key={i} severity={a.severity} />
                ))}
              </div>
            ) : (
              <SeverityBadge severity="NORMAL" />
            )}
          </div>
        </div>

        {/* Anomaly details */}
        {anomalies.length > 0 && (
          <div className="space-y-2">
            {anomalies.map((a, i) => (
              <div key={i} className={`p-3 rounded border ${SEVERITY_STYLES[a.severity]?.bg} ${SEVERITY_STYLES[a.severity]?.border}`}>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-white capitalize">
                    {a.anomaly_type.replace('_', ' ')}
                  </span>
                  <span className="text-xs text-zinc-400">{(a.confidence * 100).toFixed(0)}% confidence</span>
                </div>
                {a.location_description && (
                  <p className="text-xs text-zinc-400 mt-1">{a.location_description}</p>
                )}
              </div>
            ))}
          </div>
        )}

        {/* TTF details */}
        {ttf && (
          <div className="text-sm text-zinc-400">
            <p>
              <span className="text-zinc-300 font-medium">Estimated failure:</span>{' '}
              {ttf.days} days (range: {ttf.confidence_range.low}–{ttf.confidence_range.high})
            </p>
            <p className="text-xs mt-0.5">{ttf.failure_mode}</p>
          </div>
        )}

        {/* Recommended action */}
        <div className="bg-bg-primary/50 rounded p-3">
          <p className="text-xs text-zinc-500 mb-1">Recommended Action</p>
          <p className="text-sm text-zinc-200">{result.recommended_action}</p>
        </div>

        {/* Reasoning (expandable) */}
        {result.reasoning_chain && (
          <div>
            <button
              onClick={() => setExpanded(!expanded)}
              className="flex items-center gap-1 text-xs text-accent-blue hover:text-blue-400 transition-colors"
            >
              {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              AI Reasoning
            </button>
            {expanded && (
              <div className="mt-2 p-3 bg-bg-primary/50 rounded border border-bg-tertiary">
                <p className="text-xs text-zinc-400 font-mono leading-relaxed">
                  {result.reasoning_chain}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default function ResultsPage({ jobId, results, onNewAnalysis }: Props) {
  const { summary, equipment_results } = results;

  // Video source: demo uses static file, live jobs use API endpoint
  const videoSrc = jobId === 'demo'
    ? '/demos/demo-morph.mp4'
    : getVideoUrl(jobId);

  // Build TTF timeline chart data
  const chartData = [0, 30, 60, 90].map(day => {
    const point: Record<string, number | string> = { day: `Day ${day === 0 ? '0' : `+${day}`}` };
    equipment_results.forEach(er => {
      if (day === 0) {
        point[er.label] = er.current_state.overall_health_score;
      } else {
        const pred = er.predictions.find(p => p.horizon_days === day);
        point[er.label] = pred?.predicted_health_score ?? er.current_state.overall_health_score;
      }
    });
    return point;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-white">Analysis Complete</h2>
          <p className="text-sm text-zinc-400 mt-1">
            {summary.total_equipment_analyzed} equipment items analyzed
          </p>
        </div>
        <button
          onClick={onNewAnalysis}
          className="px-4 py-2 border border-bg-tertiary text-zinc-300 hover:text-white hover:border-zinc-500 rounded-lg text-sm transition-colors"
        >
          New Analysis
        </button>
      </div>

      {/* Video Player + Summary sidebar */}
      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2 bg-bg-secondary border border-bg-tertiary rounded-lg overflow-hidden">
          <div className="relative">
            <video
              className="w-full aspect-video bg-black"
              controls
              autoPlay
              loop
              muted
              src={videoSrc}
              poster=""
            >
              Your browser does not support video playback.
            </video>
            {/* Timeline markers overlay */}
            <div className="absolute bottom-14 left-0 right-0 flex justify-between px-4 pointer-events-none">
              {['Day 0', '+30d', '+60d', '+90d'].map((label, i) => (
                <span key={i} className="text-[10px] text-white/60 bg-black/50 px-1.5 py-0.5 rounded">
                  {label}
                </span>
              ))}
            </div>
          </div>
          <div className="px-4 py-2 flex items-center justify-between border-t border-bg-tertiary">
            <p className="text-xs text-zinc-500">
              Predicted degradation progression — 90 day forecast
            </p>
            {jobId !== 'demo' && (
              <a
                href={getVideoUrl(jobId)}
                download
                className="text-xs text-accent-blue hover:text-blue-400 flex items-center gap-1"
              >
                <Download className="w-3 h-3" />
                Download
              </a>
            )}
          </div>
        </div>

        {/* Summary sidebar */}
        <div className="space-y-3">
          <div className="bg-bg-secondary border border-bg-tertiary rounded-lg p-4 space-y-3">
            <h3 className="text-sm font-semibold text-white">Summary</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-zinc-400">Equipment</span>
                <span className="text-white font-medium">{summary.total_equipment_analyzed}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-400">Critical</span>
                <span className="text-severity-critical font-medium">{summary.critical_findings}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-400">Warnings</span>
                <span className="text-severity-warning font-medium">{summary.warning_findings}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-400">Nearest TTF</span>
                <span className="text-white font-medium">{summary.nearest_failure_days ?? '—'} days</span>
              </div>
            </div>
          </div>

          {/* Priority action in sidebar */}
          {summary.priority_action && (
            <div className="bg-severity-warning/5 border border-severity-warning/20 rounded-lg p-4">
              <div className="flex items-start gap-2">
                <Shield className="w-4 h-4 text-severity-warning flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-xs font-medium text-severity-warning">Priority Action</p>
                  <p className="text-xs text-zinc-300 mt-1">{summary.priority_action}</p>
                </div>
              </div>
            </div>
          )}

          {jobId !== 'demo' && (
            <a
              href={getVideoUrl(jobId)}
              download
              className="block w-full text-center py-2 bg-accent-blue hover:bg-blue-600 text-white rounded-lg text-sm font-medium transition-colors"
            >
              <Download className="w-4 h-4 inline mr-1" />
              Download Video
            </a>
          )}
        </div>
      </div>

      {/* TTF Timeline Chart */}
      <div className="bg-bg-secondary border border-bg-tertiary rounded-lg p-4">
        <h3 className="text-sm font-semibold text-white mb-4">
          Health Score Projection (90 Days)
        </h3>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e1e2e" />
            <XAxis dataKey="day" tick={{ fill: '#71717a', fontSize: 12 }} />
            <YAxis domain={[0, 100]} tick={{ fill: '#71717a', fontSize: 12 }} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#12121a',
                border: '1px solid #1e1e2e',
                borderRadius: '8px',
                fontSize: 12,
              }}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <ReferenceLine y={50} stroke="#ef4444" strokeDasharray="5 5" label="" />
            {equipment_results.map(er => (
              <Line
                key={er.equipment_id}
                type="monotone"
                dataKey={er.label}
                stroke={TYPE_COLORS[er.type] || '#6b7280'}
                strokeWidth={2}
                dot={{ r: 4 }}
                activeDot={{ r: 6 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
        <p className="text-xs text-zinc-500 mt-2 text-center">
          Red dashed line = critical threshold (50)
        </p>
      </div>

      {/* Equipment cards */}
      <div>
        <h3 className="text-sm font-semibold text-white mb-3">Equipment Analysis</h3>
        <div className="space-y-3">
          {equipment_results.map(er => (
            <EquipmentCard key={er.equipment_id} result={er} />
          ))}
        </div>
      </div>
    </div>
  );
}
