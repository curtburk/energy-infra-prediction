"""
Cosmos Reason inference service.

Calls Cosmos-Reason1-7B via vLLM's OpenAI-compatible API for:
  1. Equipment detection (identify transformers, bushings, insulators)
  2. Anomaly classification (oil leak, corrosion, thermal, etc.)

Requires vLLM serving Cosmos-Reason1-7B (see scripts/start_cosmos_reason.sh).
"""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import List, Optional

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)

# Default vLLM URL — Docker bridge gateway from inside containers,
# or localhost for host-network development
VLLM_URL = settings.VLLM_URL


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are an expert power grid infrastructure analyst. "
    "You analyze visual footage of electrical substation equipment "
    "for anomalies, degradation, and safety hazards. "
    "Answer the question in the following format:\n"
    "<think>\nyour reasoning\n</think>\n\n"
    "<answer>\nyour answer\n</answer>."
)

EQUIPMENT_DETECTION_PROMPT = """Analyze this substation footage and identify all visible equipment.

For each piece of equipment found, provide a JSON array with objects containing:
- "equipment_id": sequential ID like "eq-001", "eq-002"
- "type": one of "transformer", "bushing", "insulator", "circuit_breaker", "switchgear", "other"
- "label": human-readable description (e.g. "Main Power Transformer")
- "bounding_box": {"x": int, "y": int, "width": int, "height": int} in pixels
- "confidence": float 0.0-1.0

Respond with ONLY a JSON array, no other text."""

ANOMALY_CLASSIFICATION_PROMPT = """Analyze this {equipment_type} for anomalies and degradation.

Consider these anomaly types and their visual indicators:
- oil_leak: Dark staining, wet appearance, drip patterns at base or seals
- thermal_hotspot: Discoloration, warping, heat damage patterns
- corrosion: Orange/brown rust, oxidation, pitting, flaking on metal surfaces
- bushing_damage: Surface contamination, cracks, burn marks on ceramic
- insulator_degradation: Surface deposits, chips, tracking marks
- physical_damage: Dents, cracks, structural deformation
- vegetation_encroachment: Plant growth near equipment

For each anomaly found, provide a JSON object with:
- "anomalies_detected": array of objects with:
  - "anomaly_type": one of the types above
  - "severity": "CRITICAL", "WARNING", "WATCH", or "NORMAL"
  - "confidence": float 0.0-1.0
  - "location_description": where on the equipment
  - "reasoning": your analysis
- "overall_health_score": integer 0-100
- "recommended_action": string

If no anomalies, return {{"anomalies_detected": [], "overall_health_score": 95, "recommended_action": "Continue routine monitoring"}}.

Respond with ONLY a JSON object, no other text."""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class CosmosReasonService:
    """Calls Cosmos-Reason1-7B via vLLM for visual reasoning."""

    def __init__(self, vllm_url: str = None):
        self.vllm_url = vllm_url or VLLM_URL
        self.model_name = settings.COSMOS_REASON_MODEL
        self._client = httpx.AsyncClient(timeout=120.0)

    async def check_health(self) -> bool:
        """Check if vLLM is serving the model."""
        try:
            resp = await self._client.get(
                self.vllm_url.replace("/v1", "/health")
            )
            return resp.status_code == 200
        except Exception:
            return False

    async def _call_vlm(
        self,
        prompt: str,
        image_base64: str,
        max_tokens: int = 4096,
        temperature: float = 0.6,
    ) -> str:
        """Send an image + text prompt to vLLM and return the response text."""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            },
        ]

        payload = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "repetition_penalty": 1.05,
        }

        try:
            resp = await self._client.post(
                f"{self.vllm_url}/chat/completions",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            logger.error("vLLM HTTP error: %s — %s", e.response.status_code, e.response.text)
            raise
        except Exception as e:
            logger.error("vLLM call failed: %s", e)
            raise

    def _encode_frame(self, frame_path: str) -> str:
        """Read a JPEG frame and return base64 string."""
        with open(frame_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _extract_json(self, text: str) -> dict | list:
        """Extract JSON from model response, handling <answer> tags."""
        # Strip think/answer tags if present
        if "<answer>" in text:
            text = text.split("<answer>")[-1]
        if "</answer>" in text:
            text = text.split("</answer>")[0]
        # Strip markdown code fences
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())

    # -- Public API --------------------------------------------------------

    async def detect_equipment(
        self, frame_paths: List[str]
    ) -> list[dict]:
        """
        Detect equipment in video frames.

        Uses a representative frame (middle of the sequence) for detection.
        Returns list of equipment dicts matching the API schema.
        """
        if not frame_paths:
            raise ValueError("No frames provided for detection")

        # Use middle frame as representative
        mid_idx = len(frame_paths) // 2
        frame_b64 = self._encode_frame(frame_paths[mid_idx])

        logger.info("Detecting equipment in frame %d of %d", mid_idx, len(frame_paths))

        response = await self._call_vlm(
            prompt=EQUIPMENT_DETECTION_PROMPT,
            image_base64=frame_b64,
        )

        try:
            equipment_list = self._extract_json(response)
            if isinstance(equipment_list, dict):
                equipment_list = [equipment_list]
            logger.info("Detected %d equipment items", len(equipment_list))
            return equipment_list
        except json.JSONDecodeError:
            logger.error("Failed to parse equipment detection response: %s", response[:500])
            raise ValueError(f"Model returned invalid JSON: {response[:200]}")

    async def classify_anomalies(
        self,
        frame_path: str,
        equipment_type: str,
    ) -> dict:
        """
        Classify anomalies for a specific equipment type in a frame.

        Returns dict with anomalies_detected, overall_health_score, recommended_action.
        """
        frame_b64 = self._encode_frame(frame_path)

        prompt = ANOMALY_CLASSIFICATION_PROMPT.format(
            equipment_type=equipment_type
        )

        logger.info("Classifying anomalies for %s", equipment_type)

        response = await self._call_vlm(
            prompt=prompt,
            image_base64=frame_b64,
        )

        try:
            result = self._extract_json(response)
            logger.info(
                "Classification result: health=%s, anomalies=%d",
                result.get("overall_health_score", "?"),
                len(result.get("anomalies_detected", [])),
            )
            return result
        except json.JSONDecodeError:
            logger.error("Failed to parse anomaly classification: %s", response[:500])
            raise ValueError(f"Model returned invalid JSON: {response[:200]}")

    async def close(self):
        await self._client.aclose()
