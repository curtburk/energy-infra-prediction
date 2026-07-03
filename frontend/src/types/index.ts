export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface Equipment {
  equipment_id: string;
  type: string;
  label: string;
  bounding_box: BoundingBox;
  confidence: number;
  thumbnail_base64: string;
}

export interface Anomaly {
  anomaly_type: string;
  severity: 'CRITICAL' | 'WARNING' | 'WATCH' | 'NORMAL';
  confidence: number;
  location_description: string;
  bounding_box?: BoundingBox;
  progression_notes?: string;
}

export interface PredictionResult {
  horizon_days: number;
  predicted_anomalies: Anomaly[];
  predicted_health_score: number;
}

export interface TTFEstimate {
  days: number;
  confidence_range: { low: number; high: number };
  failure_mode: string;
}

export interface CurrentState {
  anomalies_detected: Anomaly[];
  overall_health_score: number;
}

export interface EquipmentResult {
  equipment_id: string;
  type: string;
  label: string;
  current_state: CurrentState;
  predictions: PredictionResult[];
  time_to_failure_estimate: TTFEstimate | null;
  recommended_action: string;
  reasoning_chain: string;
}

export interface AnalysisSummary {
  total_equipment_analyzed: number;
  critical_findings: number;
  warning_findings: number;
  watch_findings: number;
  nearest_failure_days: number | null;
  priority_action: string;
}

export interface ProgressInfo {
  stage: string | null;
  percent_complete: number;
  current_operation: string | null;
}

export interface JobStatus {
  job_id: string;
  status: string;
  progress: ProgressInfo;
  created_at: string;
  updated_at: string;
  error: string | null;
}

export interface AnalysisResults {
  job_id: string;
  analysis_completed_at: string;
  equipment_results: EquipmentResult[];
  summary: AnalysisSummary;
}

export type AppStep = 'upload' | 'equipment_selection' | 'processing' | 'results';
