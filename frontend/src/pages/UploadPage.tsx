import { useState, useRef, useCallback } from 'react';
import { Upload, Play, FileVideo, AlertCircle } from 'lucide-react';
import type { Equipment, AnalysisResults } from '../types';
import { uploadVideo, getJobStatus, getDetectedEquipment } from '../api/client';
import DEMO_RESULTS from '../data/demo-results';

interface Props {
  onUploadComplete: (jobId: string, equipment: Equipment[]) => void;
  onDemoResults: (results: AnalysisResults) => void;
  onError: (msg: string) => void;
}

export default function UploadPage({ onUploadComplete, onDemoResults, onError }: Props) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(async (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!['mp4', 'mov', 'avi'].includes(ext || '')) {
      onError('Invalid file format. Please upload MP4, MOV, or AVI.');
      return;
    }

    setUploading(true);
    setUploadProgress('Uploading video...');

    try {
      const { job_id } = await uploadVideo(file, file.name);
      setUploadProgress('Detecting equipment...');

      // Poll until detection completes
      let status = await getJobStatus(job_id);
      while (status.status === 'QUEUED' || status.status === 'DETECTING') {
        await new Promise(r => setTimeout(r, 1500));
        status = await getJobStatus(job_id);
      }

      if (status.status === 'AWAITING_CONFIRMATION') {
        const { equipment_detected } = await getDetectedEquipment(job_id);
        onUploadComplete(job_id, equipment_detected);
      } else if (status.status === 'FAILED') {
        onError(status.error || 'Detection failed');
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Upload failed';
      onError(msg);
    } finally {
      setUploading(false);
      setUploadProgress('');
    }
  }, [onUploadComplete, onError]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const handleQuickDemo = useCallback(() => {
    onDemoResults(DEMO_RESULTS);
  }, [onDemoResults]);

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      {/* Title */}
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold text-white">
          Substation Equipment Analysis
        </h2>
        <p className="text-zinc-400">
          Upload surveillance footage to detect anomalies and predict equipment degradation
        </p>
      </div>

      {/* Upload zone */}
      <div
        className={`
          relative border-2 border-dashed rounded-lg p-12 text-center transition-colors cursor-pointer
          ${dragging
            ? 'border-accent-blue bg-accent-blue/5'
            : 'border-bg-tertiary hover:border-zinc-600 bg-bg-secondary'
          }
          ${uploading ? 'pointer-events-none opacity-60' : ''}
        `}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => !uploading && inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept="video/mp4,video/quicktime,video/x-msvideo,.mp4,.mov,.avi"
          className="hidden"
          onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
        />

        {uploading ? (
          <div className="space-y-3">
            <div className="w-10 h-10 border-2 border-accent-blue border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-zinc-300">{uploadProgress}</p>
          </div>
        ) : (
          <div className="space-y-3">
            <Upload className="w-10 h-10 text-zinc-500 mx-auto" />
            <div>
              <p className="text-zinc-300">Drop video file here or click to browse</p>
              <p className="text-sm text-zinc-500 mt-1">
                MP4, MOV, AVI &middot; 10-25 seconds &middot; 720p minimum
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Divider */}
      <div className="flex items-center gap-4">
        <div className="flex-1 border-t border-bg-tertiary" />
        <span className="text-sm text-zinc-500">OR</span>
        <div className="flex-1 border-t border-bg-tertiary" />
      </div>

      {/* Quick Demo */}
      <div className="text-center">
        <button
          onClick={handleQuickDemo}
          className="inline-flex items-center gap-2 px-6 py-3 bg-accent-blue hover:bg-blue-600 text-white rounded-lg font-medium transition-colors"
        >
          <Play className="w-4 h-4" />
          Launch Quick Demo
        </button>
        <p className="text-sm text-zinc-500 mt-2">
          Pre-analyzed results &middot; No upload required
        </p>
      </div>

      {/* Info */}
      <div className="bg-bg-secondary border border-bg-tertiary rounded-lg p-4 flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-accent-blue flex-shrink-0 mt-0.5" />
        <div className="text-sm text-zinc-400">
          <p className="font-medium text-zinc-300 mb-1">On-Premises Processing</p>
          <p>
            All video analysis runs locally on HP ZGX Nano hardware using NVIDIA Cosmos AI models. 
            No data leaves this device. Zero cloud dependency.
          </p>
        </div>
      </div>
    </div>
  );
}
