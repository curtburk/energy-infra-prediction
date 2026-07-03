"""
Job Orchestrator — manages the async processing pipeline for each job.

Pipeline stages:
  1. QUEUED → DETECTING: Run Cosmos Reason for equipment detection
  2. DETECTING → AWAITING_CONFIRMATION: Wait for user to confirm equipment
  3. AWAITING_CONFIRMATION → ANALYZING: Run Cosmos Predict + Reason pipeline
  4. ANALYZING → COMPLETE: Render output video
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os

from backend.config import settings
from backend.models.job import (
    Anomaly,
    AnomalyType,
    AnalysisSummary,
    BoundingBox,
    ConfidenceRange,
    CurrentState,
    Equipment,
    EquipmentResult,
    EquipmentType,
    Job,
    JobStatus,
    PredictionResult,
    Severity,
    TimeToFailureEstimate,
)
from backend.services.mock_inference import mock_detect_equipment, mock_analyze_equipment
from backend.store.memory_store import job_store

logger = logging.getLogger(__name__)


class JobOrchestrator:
    """Coordinates async processing of analysis jobs."""

    def __init__(self):
        self._active_tasks: dict[str, asyncio.Task] = {}

    async def start_detection(self, job_id: str) -> None:
        """Launch detection as a background task."""
        task = asyncio.create_task(self._run_detection(job_id))
        self._active_tasks[job_id] = task

    async def start_analysis(self, job_id: str) -> None:
        """Launch full analysis pipeline as a background task."""
        task = asyncio.create_task(self._run_analysis(job_id))
        self._active_tasks[job_id] = task

    async def cancel(self, job_id: str) -> None:
        """Cancel a running job."""
        task = self._active_tasks.pop(job_id, None)
        if task and not task.done():
            task.cancel()

    # -- Detection pipeline ------------------------------------------------

    async def _run_detection(self, job_id: str) -> None:
        job = job_store.get(job_id)
        if not job:
            return

        try:
            job.transition(JobStatus.DETECTING)
            job.update_progress("equipment_detection", 0, "Starting equipment detection")

            async def progress_cb(stage, pct, operation):
                job.update_progress(stage, pct, operation)

            if settings.MOCK_MODELS:
                equipment = await mock_detect_equipment(
                    job.video_path or "", progress_callback=progress_cb
                )
            else:
                equipment = await self._real_detect_equipment(job, progress_cb)

            job.detected_equipment = equipment
            job.transition(JobStatus.AWAITING_CONFIRMATION)
            job.update_progress("equipment_detection", 100, "Equipment detection complete")
            logger.info("Job %s: detected %d equipment items", job_id, len(equipment))

        except Exception as e:
            logger.exception("Job %s: detection failed", job_id)
            job.fail(str(e))
        finally:
            self._active_tasks.pop(job_id, None)

    async def _real_detect_equipment(self, job: Job, progress_cb) -> list[Equipment]:
        """Run Cosmos Reason equipment detection via vLLM."""
        from backend.services.model_manager import model_manager
        from backend.services.video.extractor import extract_frames

        await progress_cb("equipment_detection", 10, "Extracting frames")

        # Extract frames from uploaded video
        frames_dir = os.path.join(settings.FRAMES_DIR, job.job_id)
        frames = extract_frames(job.video_path, frames_dir, target_fps=4)

        await progress_cb("equipment_detection", 30, "Running Cosmos Reason detection")

        # Call Cosmos Reason
        raw_results = await model_manager.reason.detect_equipment(frames)

        await progress_cb("equipment_detection", 80, "Processing results")

        # Convert raw JSON to Equipment models
        equipment = []
        for item in raw_results:
            try:
                bbox = item.get("bounding_box", {})
                eq = Equipment(
                    equipment_id=item.get("equipment_id", f"eq-{len(equipment)+1:03d}"),
                    type=EquipmentType(item.get("type", "other")),
                    label=item.get("label", "Unknown Equipment"),
                    bounding_box=BoundingBox(
                        x=bbox.get("x", 0),
                        y=bbox.get("y", 0),
                        width=bbox.get("width", 100),
                        height=bbox.get("height", 100),
                    ),
                    confidence=float(item.get("confidence", 0.5)),
                )

                # Generate thumbnail from the detection frame
                mid_frame = frames[len(frames) // 2]
                with open(mid_frame, "rb") as f:
                    eq.thumbnail_base64 = base64.b64encode(f.read()).decode("utf-8")

                equipment.append(eq)
            except Exception as e:
                logger.warning("Skipping invalid equipment item: %s — %s", item, e)

        return equipment

    # -- Analysis pipeline -------------------------------------------------

    async def _run_analysis(self, job_id: str) -> None:
        job = job_store.get(job_id)
        if not job:
            return

        try:
            job.update_progress("prediction_generation", 0, "Starting analysis pipeline")

            async def progress_cb(stage, pct, operation):
                job.update_progress(stage, pct, operation)

            if settings.MOCK_MODELS:
                results, summary = await mock_analyze_equipment(
                    job.selected_equipment_ids,
                    job.video_path or "",
                    settings.PREDICTION_HORIZONS,
                    progress_callback=progress_cb,
                )
            else:
                results, summary = await self._real_analyze_equipment(job, progress_cb)

            job.equipment_results = results
            job.analysis_summary = summary

            # Video rendering stage — generate annotated morph video
            job.update_progress("video_rendering", 50, "Rendering degradation morph video")

            output_video_path = os.path.join(
                settings.OUTPUT_DIR, f"analysis-{job_id}.mp4"
            )

            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    self._render_output_video,
                    job,
                    output_video_path,
                )
                job.output_video_path = output_video_path
                job.update_progress("video_rendering", 100, "Video rendering complete")
            except Exception as e:
                logger.warning("Video rendering failed: %s (job will complete without video)", e)
                job.update_progress("video_rendering", 100, "Complete (video unavailable)")

            job.transition(JobStatus.COMPLETE)
            logger.info("Job %s: analysis complete", job_id)

        except Exception as e:
            logger.exception("Job %s: analysis failed", job_id)
            job.fail(str(e))
        finally:
            self._active_tasks.pop(job_id, None)

    def _render_output_video(self, job: Job, output_path: str) -> None:
        """Synchronous video rendering (runs in thread executor)."""
        from backend.services.video.pipeline import process_video_output

        # Collect prediction video paths (empty for mock mode —
        # pipeline will synthesize degradation effects from the source)
        prediction_paths = getattr(job, '_prediction_video_paths', [None, None, None])

        process_video_output(
            current_video_path=job.video_path,
            prediction_video_paths=prediction_paths,
            equipment_results=job.equipment_results,
            output_path=output_path,
        )

    async def _real_analyze_equipment(self, job: Job, progress_cb):
        """Run full Cosmos pipeline: Reason classification + Predict future states."""
        from pathlib import Path
        from backend.services.model_manager import model_manager

        frames_dir = os.path.join(settings.FRAMES_DIR, job.job_id)
        frames = sorted(str(p) for p in Path(frames_dir).glob("frame_*.jpg"))
        if not frames:
            from backend.services.video.extractor import extract_frames
            frames = extract_frames(job.video_path, frames_dir, target_fps=4)

        mid_frame = frames[len(frames) // 2]
        selected = [
            eq for eq in job.detected_equipment
            if eq.equipment_id in job.selected_equipment_ids
        ]

        # We'll collect prediction video paths for the first equipment item
        # (primary subject for the morph video)
        all_prediction_paths = [None, None, None]

        total_steps = len(selected) * 2
        step = 0
        results = []

        for eq_idx, eq in enumerate(selected):
            # --- Anomaly classification via Cosmos Reason ---
            step += 1
            pct = int((step / total_steps) * 60)
            await progress_cb(
                "anomaly_classification", pct,
                f"Classifying anomalies for {eq.label}",
            )

            classification = await model_manager.reason.classify_anomalies(
                frame_path=mid_frame,
                equipment_type=eq.type.value,
            )

            # Parse classification into typed models
            anomalies = []
            for a in classification.get("anomalies_detected", []):
                try:
                    anomalies.append(Anomaly(
                        anomaly_type=AnomalyType(a.get("anomaly_type", "physical_damage")),
                        severity=Severity(a.get("severity", "WATCH")),
                        confidence=float(a.get("confidence", 0.5)),
                        location_description=a.get("location_description", ""),
                    ))
                except Exception as e:
                    logger.warning("Skipping invalid anomaly: %s — %s", a, e)

            health_score = int(classification.get("overall_health_score", 80))
            recommended_action = classification.get("recommended_action", "Monitor")
            reasoning = classification.get("reasoning", "")
            if not reasoning and anomalies:
                reasoning = f"Detected {len(anomalies)} anomaly(ies) on {eq.label}."

            # --- Future state generation via Cosmos3-Nano ---
            step += 1
            pct = int((step / total_steps) * 90)
            predictions = []

            if model_manager.predict and model_manager.predict.check_available():
                primary_anomaly = anomalies[0].anomaly_type.value if anomalies else "physical_damage"
                pred_dir = os.path.join(settings.OUTPUT_DIR, job.job_id, "predictions")

                await progress_cb(
                    "prediction_generation", pct,
                    f"Generating +30/60/90 day videos for {eq.label} (Cosmos3-Nano)",
                )

                pred_videos = await model_manager.predict.generate_degradation_sequence(
                    input_video=job.video_path,
                    equipment_type=eq.type.value,
                    anomaly_type=primary_anomaly,
                    horizons=settings.PREDICTION_HORIZONS,
                    output_dir=pred_dir,
                )

                # Store paths for the first equipment (primary morph subject)
                if eq_idx == 0:
                    all_prediction_paths = pred_videos

                for i, days in enumerate(settings.PREDICTION_HORIZONS):
                    predictions.append(PredictionResult(
                        horizon_days=days,
                        predicted_anomalies=anomalies,
                        predicted_health_score=max(0, health_score - (i + 1) * 12),
                    ))
            else:
                await progress_cb(
                    "prediction_generation", pct,
                    f"Extrapolating predictions for {eq.label}",
                )
                for i, days in enumerate(settings.PREDICTION_HORIZONS):
                    predictions.append(PredictionResult(
                        horizon_days=days,
                        predicted_anomalies=anomalies,
                        predicted_health_score=max(0, health_score - (i + 1) * 12),
                    ))

            # --- Build TTF estimate ---
            ttf = None
            if anomalies and any(a.severity in (Severity.WARNING, Severity.CRITICAL) for a in anomalies):
                ttf = TimeToFailureEstimate(
                    days=max(10, health_score),
                    confidence_range=ConfidenceRange(
                        low=max(5, health_score - 15),
                        high=health_score + 20,
                    ),
                    failure_mode=f"{anomalies[0].anomaly_type.value.replace('_', ' ').title()} progression",
                )

            results.append(EquipmentResult(
                equipment_id=eq.equipment_id,
                type=eq.type,
                label=eq.label,
                current_state=CurrentState(
                    anomalies_detected=anomalies,
                    overall_health_score=health_score,
                ),
                predictions=predictions,
                time_to_failure_estimate=ttf,
                recommended_action=recommended_action,
                reasoning_chain=reasoning,
            ))

        # Store prediction video paths on job for the video renderer
        job._prediction_video_paths = all_prediction_paths

        # Build summary
        critical = sum(1 for r in results for a in r.current_state.anomalies_detected if a.severity == Severity.CRITICAL)
        warning = sum(1 for r in results for a in r.current_state.anomalies_detected if a.severity == Severity.WARNING)
        watch = sum(1 for r in results for a in r.current_state.anomalies_detected if a.severity == Severity.WATCH)
        ttf_days = [r.time_to_failure_estimate.days for r in results if r.time_to_failure_estimate]

        summary = AnalysisSummary(
            total_equipment_analyzed=len(results),
            critical_findings=critical,
            warning_findings=warning,
            watch_findings=watch,
            nearest_failure_days=min(ttf_days) if ttf_days else None,
            priority_action=results[0].recommended_action if results else "No action required",
        )

        return results, summary


# Singleton
orchestrator = JobOrchestrator()
