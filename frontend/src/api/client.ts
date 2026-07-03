import axios from 'axios';
import type { AnalysisResults, Equipment, JobStatus } from '../types';

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
});

export async function uploadVideo(
  file: File,
  name?: string,
  description?: string,
): Promise<{ job_id: string }> {
  const form = new FormData();
  form.append('file', file);
  if (name) form.append('name', name);
  if (description) form.append('description', description);

  const { data } = await api.post('/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  });
  return data;
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const { data } = await api.get(`/jobs/${jobId}/status`);
  return data;
}

export async function getDetectedEquipment(
  jobId: string,
): Promise<{ equipment_detected: Equipment[]; frame_preview_base64: string }> {
  const { data } = await api.get(`/jobs/${jobId}/equipment`);
  return data;
}

export async function confirmEquipment(
  jobId: string,
  equipmentIds: string[],
  horizons: number[] = [30, 60, 90],
): Promise<void> {
  await api.post(`/jobs/${jobId}/confirm`, {
    selected_equipment_ids: equipmentIds,
    analysis_options: {
      prediction_horizons: horizons,
      include_severity_assessment: true,
    },
  });
}

export async function getResults(jobId: string): Promise<AnalysisResults> {
  const { data } = await api.get(`/jobs/${jobId}/results`);
  return data;
}

export function getVideoUrl(jobId: string): string {
  return `/api/v1/jobs/${jobId}/video`;
}

export async function cancelJob(jobId: string): Promise<void> {
  await api.delete(`/jobs/${jobId}`);
}
