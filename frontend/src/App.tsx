import { useState, useCallback } from 'react';
import type { AppStep, Equipment, AnalysisResults, JobStatus } from './types';
import UploadPage from './pages/UploadPage';
import EquipmentSelectionPage from './pages/EquipmentSelectionPage';
import ProcessingPage from './pages/ProcessingPage';
import ResultsPage from './pages/ResultsPage';
import { Zap } from 'lucide-react';

export default function App() {
  const [step, setStep] = useState<AppStep>('upload');
  const [jobId, setJobId] = useState<string | null>(null);
  const [equipment, setEquipment] = useState<Equipment[]>([]);
  const [results, setResults] = useState<AnalysisResults | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleReset = useCallback(() => {
    setStep('upload');
    setJobId(null);
    setEquipment([]);
    setResults(null);
    setError(null);
  }, []);

  const handleUploadComplete = useCallback((id: string, eq: Equipment[]) => {
    setJobId(id);
    setEquipment(eq);
    setStep('equipment_selection');
  }, []);

  const handleConfirmed = useCallback(() => {
    setStep('processing');
  }, []);

  const handleAnalysisComplete = useCallback((r: AnalysisResults) => {
    setResults(r);
    setStep('results');
  }, []);

  const handleDemoResults = useCallback((r: AnalysisResults) => {
    setResults(r);
    setJobId('demo');
    setStep('results');
  }, []);

  return (
    <div className="min-h-screen bg-bg-primary">
      {/* Header */}
      <header className="border-b border-bg-tertiary px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Zap className="w-6 h-6 text-accent-blue" />
            <div>
              <h1 className="text-lg font-semibold text-white">
                Grid Infrastructure Anomaly Prediction
              </h1>
              <p className="text-xs text-zinc-500">
                HP ZGX Nano &middot; NVIDIA Cosmos AI
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            {step !== 'upload' && (
              <button
                onClick={handleReset}
                className="text-sm text-zinc-400 hover:text-white transition-colors"
              >
                New Analysis
              </button>
            )}
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-severity-normal" />
              <span className="text-xs text-zinc-500">On-Premises</span>
            </div>
          </div>
        </div>
      </header>

      {/* Error banner */}
      {error && (
        <div className="bg-severity-critical/10 border-b border-severity-critical/30 px-6 py-3">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <p className="text-sm text-severity-critical">{error}</p>
            <button onClick={() => setError(null)} className="text-severity-critical text-sm">
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* Page content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {step === 'upload' && (
          <UploadPage
            onUploadComplete={handleUploadComplete}
            onDemoResults={handleDemoResults}
            onError={setError}
          />
        )}
        {step === 'equipment_selection' && jobId && (
          <EquipmentSelectionPage
            jobId={jobId}
            equipment={equipment}
            onConfirmed={handleConfirmed}
            onCancel={handleReset}
            onError={setError}
          />
        )}
        {step === 'processing' && jobId && (
          <ProcessingPage
            jobId={jobId}
            onComplete={handleAnalysisComplete}
            onError={(msg) => { setError(msg); handleReset(); }}
          />
        )}
        {step === 'results' && results && (
          <ResultsPage
            jobId={jobId || 'demo'}
            results={results}
            onNewAnalysis={handleReset}
          />
        )}
      </main>
    </div>
  );
}
