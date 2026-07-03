import { useState, useCallback } from 'react';
import { CheckSquare, Square, ArrowRight, X } from 'lucide-react';
import type { Equipment } from '../types';
import { confirmEquipment } from '../api/client';

interface Props {
  jobId: string;
  equipment: Equipment[];
  onConfirmed: () => void;
  onCancel: () => void;
  onError: (msg: string) => void;
}

export default function EquipmentSelectionPage({
  jobId, equipment, onConfirmed, onCancel, onError,
}: Props) {
  const [selected, setSelected] = useState<Set<string>>(
    new Set(equipment.map(e => e.equipment_id))
  );
  const [confirming, setConfirming] = useState(false);

  const toggle = useCallback((id: string) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const handleConfirm = useCallback(async () => {
    if (selected.size === 0) {
      onError('Select at least one equipment item');
      return;
    }
    setConfirming(true);
    try {
      await confirmEquipment(jobId, Array.from(selected));
      onConfirmed();
    } catch (err: any) {
      onError(err.response?.data?.detail || 'Confirmation failed');
    } finally {
      setConfirming(false);
    }
  }, [jobId, selected, onConfirmed, onError]);

  const typeColors: Record<string, string> = {
    transformer: 'border-blue-500 bg-blue-500/10',
    bushing: 'border-purple-500 bg-purple-500/10',
    insulator: 'border-cyan-500 bg-cyan-500/10',
    circuit_breaker: 'border-amber-500 bg-amber-500/10',
    other: 'border-zinc-500 bg-zinc-500/10',
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-accent-blue font-medium">Step 2 of 4</p>
          <h2 className="text-xl font-semibold text-white mt-1">
            Confirm Equipment for Analysis
          </h2>
          <p className="text-sm text-zinc-400 mt-1">
            {equipment.length} equipment items detected. Select which to analyze.
          </p>
        </div>
        <button onClick={onCancel} className="text-zinc-400 hover:text-white">
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Equipment cards */}
      <div className="grid gap-3">
        {equipment.map(eq => {
          const isSelected = selected.has(eq.equipment_id);
          const colorClass = typeColors[eq.type] || typeColors.other;

          return (
            <button
              key={eq.equipment_id}
              onClick={() => toggle(eq.equipment_id)}
              className={`
                flex items-center gap-4 p-4 rounded-lg border text-left transition-all
                ${isSelected
                  ? `${colorClass} border-opacity-100`
                  : 'border-bg-tertiary bg-bg-secondary hover:border-zinc-600'
                }
              `}
            >
              {isSelected
                ? <CheckSquare className="w-5 h-5 text-accent-blue flex-shrink-0" />
                : <Square className="w-5 h-5 text-zinc-500 flex-shrink-0" />
              }
              <div className="flex-1 min-w-0">
                <p className="font-medium text-white">{eq.label}</p>
                <p className="text-sm text-zinc-400 capitalize">{eq.type.replace('_', ' ')}</p>
              </div>
              <div className="text-right">
                <p className="text-sm text-zinc-300">{(eq.confidence * 100).toFixed(0)}%</p>
                <p className="text-xs text-zinc-500">confidence</p>
              </div>
            </button>
          );
        })}
      </div>

      {/* Analysis options */}
      <div className="bg-bg-secondary border border-bg-tertiary rounded-lg p-4">
        <p className="text-sm font-medium text-zinc-300 mb-2">Prediction Horizons</p>
        <div className="flex gap-3">
          {[30, 60, 90].map(d => (
            <span
              key={d}
              className="px-3 py-1 rounded bg-accent-blue/10 border border-accent-blue/30 text-sm text-accent-blue"
            >
              +{d} days
            </span>
          ))}
        </div>
      </div>

      {/* Confirm button */}
      <button
        onClick={handleConfirm}
        disabled={confirming || selected.size === 0}
        className="w-full flex items-center justify-center gap-2 py-3 bg-accent-blue hover:bg-blue-600 disabled:bg-zinc-700 disabled:text-zinc-500 text-white rounded-lg font-medium transition-colors"
      >
        {confirming ? (
          <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
        ) : (
          <>
            Start Analysis
            <ArrowRight className="w-4 h-4" />
          </>
        )}
      </button>
    </div>
  );
}
