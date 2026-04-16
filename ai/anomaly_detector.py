"""
Anomaly detection module.

Current implementation: z-score on cost_history (statistical baseline).
Structured for drop-in replacement with scikit-learn IsolationForest or PyOD.
"""
from __future__ import annotations

import math
import logging
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """
    Detects anomalous cost patterns in resource history.

    To plug in a real ML model:
        1. Extract features via _extract_features()
        2. Load/train a model in __init__
        3. Replace _zscore_detect() call with model.predict()
    """

    Z_THRESHOLD = 2.0       # std deviations above mean = anomaly
    MIN_HISTORY_POINTS = 5  # need at least this many points to detect

    def detect(self, resources: list) -> List[Dict[str, Any]]:
        anomalies = []
        for resource in resources:
            cost_pts = resource.metrics.cost_history
            if len(cost_pts) < self.MIN_HISTORY_POINTS:
                continue
            values = [p.value for p in cost_pts]
            detected = self._zscore_detect(values)
            if detected:
                anomalies.append({
                    "resource_id": resource.id,
                    "resource_name": resource.name,
                    "resource_type": resource.type,
                    "anomaly_type": "cost_spike",
                    "detected_at": datetime.utcnow().isoformat(),
                    "z_score": detected["z_score"],
                    "current_value": detected["value"],
                    "mean": detected["mean"],
                    "std": detected["std"],
                    "description": (
                        f"{resource.name} daily cost ${detected['value']:.4f} is "
                        f"{detected['z_score']:.1f}σ above the {len(values)}-day mean "
                        f"(${detected['mean']:.4f})."
                    ),
                })
        return anomalies

    def _zscore_detect(self, values: List[float]) -> Dict[str, float] | None:
        n = len(values)
        mean = sum(values) / n
        variance = sum((v - mean) ** 2 for v in values) / n
        std = math.sqrt(variance)
        if std == 0:
            return None
        latest = values[-1]
        z = (latest - mean) / std
        if z >= self.Z_THRESHOLD:
            return {"z_score": round(z, 3), "value": latest, "mean": mean, "std": std}
        return None

    def _extract_features(self, resource) -> List[float]:
        """
        Feature vector for ML models.
        Extend this as you add more signals.
        """
        m = resource.metrics
        return [
            m.cpu_utilization or 0.0,
            m.network_in_mbps or 0.0,
            m.network_out_mbps or 0.0,
            resource.cost_daily,
            resource.cost_monthly,
        ]
