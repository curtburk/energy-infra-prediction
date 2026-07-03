import { useState, useEffect, useRef } from 'react';
import { Check, Circle, Loader2 } from 'lucide-react';
import type { AnalysisResults, JobStatus } from '../types';
import { getJobStatus, getResults } from '../api/client';

interface Props {
  jobId: string;
  onComplete: (results: AnalysisResults) => void;
  onError: (msg: string) => void;
}

const STAGES = [
  { id: 'equipment_detection', label: 'Equipment Detection' },
  { id: 'prediction_generation', label: 'Future State Prediction' },
  { id: 'anomaly_classification', label: 'Anomaly Classification' },
  { id: 'video_rendering', label: 'Video Rendering' },
];

export default function ProcessingPage({ jobId, onComplete, onError }: Props) {
  const [status, setStatus] = useState<JobStatus | null>(null);
  const intervalRef = useRef<number | null>(null);

  useEffect(() => {
    const poll = async () => {
      try {
        const s = await getJobStatus(jobId);
        setStatus(s);

        if (s.status === 'COMPLETE') {
          if (intervalRef.current) clearInterval(intervalRef.current);
          const results = await getResults(jobId);
          onComplete(results);
        } else if (s.status === 'FAILED') {
          if (intervalRef.current) clearInterval(intervalRef.current);
          onError(s.error || 'Analysis failed');
        }
      } catch (err) {
        // Ignore transient errors during polling
      }
    };

    poll();
    intervalRef.current = window.setInterval(poll, 2000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [jobId, onComplete, onError]);

  const currentStage = status?.progress?.stage || '';
  const percent = status?.progress?.percent_complete || 0;
  const operation = status?.progress?.current_operation || 'Initializing...';

  const getStageStatus = (stageId: string): 'pending' | 'active' | 'complete' => {
    const stageIdx = STAGES.findIndex(s => s.id === stageId);
    const currentIdx = STAGES.findIndex(s => s.id === currentStage);
    if (currentIdx < 0) return stageIdx === 0 ? 'active' : 'pending';
    if (stageIdx < currentIdx) return 'complete';
    if (stageIdx === currentIdx) return percent >= 100 ? 'complete' : 'active';
    return 'pending';
  };

  return (
    <div className="max-w-lg mx-auto text-center space-y-8 py-12">
      {/* Animated logo */}
      <div className="flex justify-center">
        <div className="w-16 h-16 rounded-2xl bg-accent-blue/10 border border-accent-blue/30 flex items-center justify-center animate-pulse-progress">
          <Loader2 className="w-8 h-8 text-accent-blue animate-spin" />
        </div>
      </div>

      <div>
        <h2 className="text-xl font-semibold text-white">Analyzing Infrastructure</h2>
        <p className="text-sm text-zinc-400 mt-1">{operation}</p>
      </div>

      {/* Progress bar */}
      <div className="space-y-2">
        <div className="w-full h-2 bg-bg-tertiary rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-accent-blue to-accent-cyan rounded-full transition-all duration-500"
            style={{ width: `${percent}%` }}
          />
        </div>
        <p className="text-sm text-zinc-500">{percent}%</p>
      </div>

      {/* Stage list */}
      <div className="bg-bg-secondary border border-bg-tertiary rounded-lg p-4 text-left">
        <div className="space-y-3">
          {STAGES.map(stage => {
            const state = getStageStatus(stage.id);
            return (
              <div key={stage.id} className="flex items-center gap-3">
                {state === 'complete' && (
                  <Check className="w-4 h-4 text-severity-normal flex-shrink-0" />
                )}
                {state === 'active' && (
                  <Loader2 className="w-4 h-4 text-accent-blue animate-spin flex-shrink-0" />
                )}
                {state === 'pending' && (
                  <Circle className="w-4 h-4 text-zinc-600 flex-shrink-0" />
                )}
                <span className={`text-sm ${
                  state === 'complete' ? 'text-zinc-300' :
                  state === 'active' ? 'text-white font-medium' :
                  'text-zinc-500'
                }`}>
                  {stage.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
