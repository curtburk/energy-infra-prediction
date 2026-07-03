"""
Mock inference service for development and testing without GPU hardware.

Returns realistic-looking synthetic results that match the API schema,
allowing full frontend and backend integration testing.
"""

from __future__ import annotations

import asyncio
import logging
from typing import List

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
    PredictionResult,
    Severity,
    TimeToFailureEstimate,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mock equipment detection
# ---------------------------------------------------------------------------

_MOCK_EQUIPMENT = [
    Equipment(
        equipment_id="eq-001",
        type=EquipmentType.TRANSFORMER,
        label="Main Power Transformer",
        bounding_box=BoundingBox(x=120, y=80, width=340, height=280),
        confidence=0.94,
        thumbnail_base64="",
    ),
    Equipment(
        equipment_id="eq-002",
        type=EquipmentType.BUSHING,
        label="High-Voltage Bushing (North)",
        bounding_box=BoundingBox(x=480, y=60, width=85, height=150),
        confidence=0.87,
        thumbnail_base64="",
    ),
    Equipment(
        equipment_id="eq-003",
        type=EquipmentType.INSULATOR,
        label="Line Insulator String",
        bounding_box=BoundingBox(x=700, y=40, width=60, height=200),
        confidence=0.81,
        thumbnail_base64="",
    ),
]


async def mock_detect_equipment(
    video_path: str,
    progress_callback=None,
) -> List[Equipment]:
    """Simulate Cosmos Reason equipment detection."""
    logger.info("Mock: detecting equipment in %s", video_path)

    # Simulate processing time
    for pct in (10, 30, 50, 70, 90, 100):
        if progress_callback:
            await progress_callback("equipment_detection", pct, f"Scanning frame {pct}%")
        await asyncio.sleep(0.3)

    # Always return first 2 items for deterministic demo behavior
    return _MOCK_EQUIPMENT[:2]


# ---------------------------------------------------------------------------
# Mock anomaly classification + prediction
# ---------------------------------------------------------------------------

_TRANSFORMER_RESULT = EquipmentResult(
    equipment_id="eq-001",
    type=EquipmentType.TRANSFORMER,
    label="Main Power Transformer",
    current_state=CurrentState(
        anomalies_detected=[
            Anomaly(
                anomaly_type=AnomalyType.OIL_LEAK,
                severity=Severity.WARNING,
                confidence=0.89,
                location_description="Base seal, southwest corner",
                bounding_box=BoundingBox(x=180, y=320, width=45, height=30),
            )
        ],
        overall_health_score=72,
    ),
    predictions=[
        PredictionResult(
            horizon_days=30,
            predicted_anomalies=[
                Anomaly(
                    anomaly_type=AnomalyType.OIL_LEAK,
                    severity=Severity.WARNING,
                    confidence=0.85,
                    progression_notes="Leak area expected to expand 15-20%",
                )
            ],
            predicted_health_score=68,
        ),
        PredictionResult(
            horizon_days=60,
            predicted_anomalies=[
                Anomaly(
                    anomaly_type=AnomalyType.OIL_LEAK,
                    severity=Severity.CRITICAL,
                    confidence=0.78,
                    progression_notes="Oil level may drop below safe threshold",
                )
            ],
            predicted_health_score=51,
        ),
        PredictionResult(
            horizon_days=90,
            predicted_anomalies=[
                Anomaly(
                    anomaly_type=AnomalyType.OIL_LEAK,
                    severity=Severity.CRITICAL,
                    confidence=0.72,
                    progression_notes="Risk of thermal runaway if unaddressed",
                ),
                Anomaly(
                    anomaly_type=AnomalyType.THERMAL_HOTSPOT,
                    severity=Severity.CRITICAL,
                    confidence=0.65,
                    progression_notes="Secondary thermal anomaly likely due to oil loss",
                ),
            ],
            predicted_health_score=34,
        ),
    ],
    time_to_failure_estimate=TimeToFailureEstimate(
        days=52,
        confidence_range=ConfidenceRange(low=38, high=71),
        failure_mode="Transformer oil depletion leading to overheating",
    ),
    recommended_action="Schedule maintenance within 30 days to reseal base gasket",
    reasoning_chain=(
        "Observed oil residue pattern at base indicates slow seal degradation. "
        "Historical progression rates for similar failures suggest 45-60 day window "
        "before critical oil loss. Thermal modeling indicates secondary hotspot "
        "development likely after 40% oil reduction."
    ),
)

_BUSHING_RESULT = EquipmentResult(
    equipment_id="eq-002",
    type=EquipmentType.BUSHING,
    label="High-Voltage Bushing (North)",
    current_state=CurrentState(
        anomalies_detected=[],
        overall_health_score=89,
    ),
    predictions=[
        PredictionResult(horizon_days=30, predicted_anomalies=[], predicted_health_score=87),
        PredictionResult(horizon_days=60, predicted_anomalies=[], predicted_health_score=85),
        PredictionResult(horizon_days=90, predicted_anomalies=[], predicted_health_score=82),
    ],
    time_to_failure_estimate=None,
    recommended_action="Continue routine monitoring",
    reasoning_chain=(
        "Bushing surface shows no signs of contamination, tracking marks, or physical damage. "
        "Porcelain housing intact with no visible cracks. Expected gradual weathering consistent "
        "with normal aging. No intervention required at this time."
    ),
)

_INSULATOR_RESULT = EquipmentResult(
    equipment_id="eq-003",
    type=EquipmentType.INSULATOR,
    label="Line Insulator String",
    current_state=CurrentState(
        anomalies_detected=[
            Anomaly(
                anomaly_type=AnomalyType.INSULATOR_DEGRADATION,
                severity=Severity.WATCH,
                confidence=0.71,
                location_description="Third disc from top, surface deposits",
            )
        ],
        overall_health_score=81,
    ),
    predictions=[
        PredictionResult(
            horizon_days=30,
            predicted_anomalies=[
                Anomaly(
                    anomaly_type=AnomalyType.INSULATOR_DEGRADATION,
                    severity=Severity.WATCH,
                    confidence=0.68,
                    progression_notes="Surface deposits may increase with seasonal pollen",
                )
            ],
            predicted_health_score=79,
        ),
        PredictionResult(horizon_days=60, predicted_anomalies=[], predicted_health_score=77),
        PredictionResult(horizon_days=90, predicted_anomalies=[], predicted_health_score=75),
    ],
    time_to_failure_estimate=None,
    recommended_action="Include in next inspection cycle",
    reasoning_chain=(
        "Minor surface deposits detected on third insulator disc. Pattern consistent with "
        "environmental contamination rather than electrical tracking. Recommend visual "
        "inspection during next scheduled maintenance window."
    ),
)

_MOCK_RESULTS = {
    "eq-001": _TRANSFORMER_RESULT,
    "eq-002": _BUSHING_RESULT,
    "eq-003": _INSULATOR_RESULT,
}


async def mock_analyze_equipment(
    equipment_ids: List[str],
    video_path: str,
    prediction_horizons: List[int],
    progress_callback=None,
) -> tuple[List[EquipmentResult], AnalysisSummary]:
    """Simulate full Cosmos pipeline: Predict + Reason classification."""
    logger.info("Mock: analyzing equipment %s", equipment_ids)

    total_steps = len(equipment_ids) * 4  # detect + 3 horizons per equipment
    step = 0

    results = []
    for eq_id in equipment_ids:
        # Simulate prediction generation
        for horizon in prediction_horizons:
            step += 1
            pct = int((step / total_steps) * 100)
            if progress_callback:
                await progress_callback(
                    "prediction_generation",
                    pct,
                    f"Generating +{horizon} day prediction for {eq_id}",
                )
            await asyncio.sleep(0.5)

        # Simulate classification
        step += 1
        pct = int((step / total_steps) * 100)
        if progress_callback:
            await progress_callback(
                "anomaly_classification",
                pct,
                f"Classifying anomalies for {eq_id}",
            )
        await asyncio.sleep(0.3)

        result = _MOCK_RESULTS.get(eq_id)
        if result:
            results.append(result)

    # Build summary from typed CurrentState objects
    critical = sum(
        1
        for r in results
        for a in r.current_state.anomalies_detected
        if a.severity == Severity.CRITICAL
    )
    warning = sum(
        1
        for r in results
        for a in r.current_state.anomalies_detected
        if a.severity == Severity.WARNING
    )
    watch = sum(
        1
        for r in results
        for a in r.current_state.anomalies_detected
        if a.severity == Severity.WATCH
    )
    ttf_days = [
        r.time_to_failure_estimate.days
        for r in results
        if r.time_to_failure_estimate
    ]

    summary = AnalysisSummary(
        total_equipment_analyzed=len(results),
        critical_findings=critical,
        warning_findings=warning,
        watch_findings=watch,
        nearest_failure_days=min(ttf_days) if ttf_days else None,
        priority_action=(
            results[0].recommended_action if results else "No action required"
        ),
    )

    return results, summary
