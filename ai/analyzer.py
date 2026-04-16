"""
AI Analyzer — rule-based engine structured for ML plug-in.

Architecture:
  analyze_resources()
    → RuleEngine.evaluate()          (current: rules, future: feature extraction → model)
    → AnomalyDetector.detect()       (current: z-score, future: Isolation Forest)
    → CostPredictor.predict()        (current: linear trend, future: LSTM/Prophet)
    → RecommendationBuilder.build()
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import List

from .anomaly_detector import AnomalyDetector
from .cost_predictor import CostPredictor
from .recommendations import RecommendationBuilder
from .rule_engine import RuleEngine

logger = logging.getLogger(__name__)


class AIAnalyzer:
    """
    Orchestrates the full analysis pipeline.
    Stateless — safe to call concurrently.
    """

    def __init__(self):
        self.rule_engine = RuleEngine()
        self.anomaly_detector = AnomalyDetector()
        self.cost_predictor = CostPredictor()
        self.rec_builder = RecommendationBuilder()

    def analyze(self, resources: list) -> dict:
        """
        Main entry point.

        Args:
            resources: list of Resource Pydantic objects

        Returns:
            {
                "recommendations": [Recommendation, ...],
                "anomalies": [dict, ...],
                "cost_forecast": dict,
                "summary": dict,
            }
        """
        logger.info("Starting analysis of %d resources", len(resources))

        rule_findings = self.rule_engine.evaluate(resources)
        anomalies = self.anomaly_detector.detect(resources)
        forecast = self.cost_predictor.forecast(resources)
        recommendations = self.rec_builder.build(resources, rule_findings, anomalies)

        total_savings = sum(r.get("estimated_savings_monthly", 0) for r in recommendations)
        summary = {
            "analyzed_at": datetime.utcnow().isoformat(),
            "resource_count": len(resources),
            "recommendation_count": len(recommendations),
            "anomaly_count": len(anomalies),
            "total_potential_savings_monthly": round(total_savings, 2),
            "total_potential_savings_annual": round(total_savings * 12, 2),
        }

        logger.info(
            "Analysis complete — %d recommendations, $%.0f/mo potential savings",
            len(recommendations), total_savings
        )
        return {
            "recommendations": recommendations,
            "anomalies": anomalies,
            "cost_forecast": forecast,
            "summary": summary,
        }
