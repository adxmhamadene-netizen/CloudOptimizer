"""
Bridge between the FastAPI backend and the AI module.
Handles caching, async wrapping, and alert generation.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from functools import lru_cache
from typing import List, Dict, Any, Optional

from ..config import settings
from ..models.recommendation import Recommendation, RecommendedAction, ApprovalStatus
from ..models.alert import Alert, AlertType, AlertSeverity
from .aws_service import AWSService
from .slack_service import SlackService

logger = logging.getLogger(__name__)

# Simple in-memory cache
_cache: Dict[str, Any] = {}
_cache_ts: Optional[datetime] = None


def _cache_valid() -> bool:
    if _cache_ts is None:
        return False
    age = (datetime.utcnow() - _cache_ts).total_seconds()
    return age < settings.CACHE_TTL_SECONDS


class AnalyzerService:
    def __init__(self):
        self.aws = AWSService()
        self.slack = SlackService()
        self._stored_recommendations: Dict[str, Recommendation] = {}

    async def run_analysis(self, force_refresh: bool = False) -> Dict[str, Any]:
        global _cache, _cache_ts

        if not force_refresh and _cache_valid() and _cache:
            logger.debug("Returning cached analysis")
            return _cache

        # Fetch resources (async-safe with run_in_executor for boto3 sync calls)
        resources = await self.aws.get_resources()

        # Run AI analysis in executor to avoid blocking event loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._run_ai, resources)

        # Hydrate recommendations to Pydantic models and store
        recommendations = []
        for rec_dict in result.get("recommendations", []):
            rec = self._dict_to_recommendation(rec_dict)
            self._stored_recommendations[rec.id] = rec
            recommendations.append(rec)

        result["recommendations"] = [r.dict() for r in recommendations]
        _cache = result
        _cache_ts = datetime.utcnow()

        # Fire-and-forget: send high-priority alerts to Slack
        asyncio.create_task(self._send_alerts(recommendations, result.get("anomalies", [])))

        return result

    def _run_ai(self, resources):
        # Import here to keep the AI module decoupled from the backend package
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))
        from ai.analyzer import AIAnalyzer
        return AIAnalyzer().analyze(resources)

    async def get_recommendations(self) -> List[Recommendation]:
        result = await self.run_analysis()
        return list(self._stored_recommendations.values())

    async def get_recommendation(self, rec_id: str) -> Optional[Recommendation]:
        if rec_id not in self._stored_recommendations:
            await self.run_analysis()
        return self._stored_recommendations.get(rec_id)

    async def approve_recommendation(
        self, rec_id: str, approved: bool, approver: str, notes: Optional[str] = None
    ) -> Optional[Recommendation]:
        rec = await self.get_recommendation(rec_id)
        if not rec:
            return None
        rec.approval_status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        rec.approved_by = approver
        self._stored_recommendations[rec_id] = rec

        if rec.slack_message_ts:
            await self.slack.update_approval_message(
                settings.SLACK_APPROVAL_CHANNEL,
                rec.slack_message_ts,
                approved,
                approver,
            )

        if approved and settings.AUTO_EXECUTE_ACTIONS:
            asyncio.create_task(self._execute_recommendation(rec))

        return rec

    async def _execute_recommendation(self, rec: Recommendation) -> None:
        for action in rec.actions:
            result = await self._execute_action(action, rec)
            await self.slack.post_execution_result(
                rec, result["success"], result.get("message", ""),
                thread_ts=rec.slack_message_ts
            )
            if result["success"]:
                rec.approval_status = ApprovalStatus.EXECUTED
                rec.executed_at = datetime.utcnow()
            else:
                rec.approval_status = ApprovalStatus.FAILED
            self._stored_recommendations[rec.id] = rec

    async def _execute_action(self, action: RecommendedAction, rec: Recommendation) -> Dict[str, Any]:
        params = action.execution_params
        action_type = action.action_type
        try:
            if action_type == "stop_instance":
                res = await self.aws.stop_ec2_instance(params.get("resource_id", ""))
                return {"success": res.get("success", False), "message": f"Stop result: {res}"}
            elif action_type == "rightsize":
                res = await self.aws.resize_ec2_instance(
                    params.get("resource_id", ""),
                    params.get("new_instance_type", ""),
                )
                return {"success": res.get("success", False), "message": f"Resize result: {res}"}
            else:
                return {"success": False, "message": f"Action {action_type} not yet automated"}
        except Exception as e:
            logger.error("Action execution failed: %s", e)
            return {"success": False, "message": str(e)}

    async def _send_alerts(self, recommendations: List[Recommendation], anomalies: list) -> None:
        for rec in recommendations:
            if rec.priority in ("critical", "high") and rec.approval_status == ApprovalStatus.PENDING:
                ts = await self.slack.send_approval_request(rec)
                if ts:
                    rec.slack_message_ts = ts
                    self._stored_recommendations[rec.id] = rec

        for anomaly in anomalies:
            alert = Alert(
                id=str(uuid.uuid4()),
                type=AlertType.ANOMALY_DETECTED,
                severity=AlertSeverity.WARNING,
                title=f"Cost anomaly: {anomaly.get('resource_name', 'unknown')}",
                message=anomaly.get("description", ""),
                resource_id=anomaly.get("resource_id"),
                resource_name=anomaly.get("resource_name"),
                metadata=anomaly,
            )
            await self.slack.send_alert(alert)

    @staticmethod
    def _dict_to_recommendation(d: Dict[str, Any]) -> Recommendation:
        actions = [RecommendedAction(**a) for a in d.get("actions", [])]
        return Recommendation(
            id=d["id"],
            resource_id=d["resource_id"],
            resource_name=d["resource_name"],
            resource_type=d["resource_type"],
            region=d.get("region", ""),
            priority=d["priority"],
            title=d["title"],
            description=d["description"],
            current_monthly_cost=d["current_monthly_cost"],
            estimated_savings_monthly=d["estimated_savings_monthly"],
            confidence_score=d.get("confidence_score", 0.7),
            actions=actions,
            reasoning=d.get("reasoning", []),
        )
