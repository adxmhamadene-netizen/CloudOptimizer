"""
Recommendation builder — converts rule findings + anomalies into actionable
Recommendation objects with estimated savings, actions, and confidence scores.
"""
from __future__ import annotations

import uuid
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


# Map rule_id → (action_type, risk, reversible, savings_factor)
RULE_ACTION_MAP = {
    "IDLE_INSTANCE": {
        "action_type": "stop_instance",
        "risk": "low",
        "reversible": True,
        "savings_factor": 1.0,   # full cost savings if stopped
        "priority_fn": lambda cost: "critical" if cost > 500 else ("high" if cost > 100 else "medium"),
    },
    "UNDERUTILIZED_INSTANCE": {
        "action_type": "rightsize",
        "risk": "medium",
        "reversible": True,
        "savings_factor": 0.45,
        "priority_fn": lambda cost: "high" if cost > 200 else "medium",
    },
    "IDLE_NETWORK": {
        "action_type": "stop_instance",
        "risk": "low",
        "reversible": True,
        "savings_factor": 0.9,
        "priority_fn": lambda cost: "medium",
    },
    "MISSING_COST_TAG": {
        "action_type": "schedule_shutdown",
        "risk": "low",
        "reversible": True,
        "savings_factor": 0.0,
        "priority_fn": lambda cost: "low",
    },
    "RESERVED_INSTANCE_OPPORTUNITY": {
        "action_type": "purchase_reserved",
        "risk": "medium",
        "reversible": False,
        "savings_factor": 0.40,
        "priority_fn": lambda cost: "medium",
    },
}

DOWNSIZE_MAP = {
    "m5.2xlarge": "m5.xlarge",
    "m5.xlarge": "m5.large",
    "m5.large": "t3.large",
    "c5.2xlarge": "c5.xlarge",
    "c5.xlarge": "c5.large",
    "r5.large": "t3.large",
    "t3.large": "t3.medium",
    "t3.medium": "t3.small",
}


class RecommendationBuilder:
    def build(
        self,
        resources: list,
        findings: list,
        anomalies: List[Dict[str, Any]],
    ) -> list:
        resource_map = {r.id: r for r in resources}
        recs = []

        # Deduplicate: one recommendation per (resource, rule)
        seen = set()
        for finding in findings:
            key = (finding.resource_id, finding.rule_id)
            if key in seen:
                continue
            seen.add(key)

            resource = resource_map.get(finding.resource_id)
            if not resource:
                continue

            rec = self._build_from_finding(finding, resource)
            if rec:
                recs.append(rec)

        # Anomaly-derived recommendations
        for anomaly in anomalies:
            resource = resource_map.get(anomaly["resource_id"])
            if resource:
                rec = self._build_from_anomaly(anomaly, resource)
                if rec:
                    recs.append(rec)

        # Sort by savings descending
        recs.sort(key=lambda r: r["estimated_savings_monthly"], reverse=True)
        return recs

    def _build_from_finding(self, finding, resource) -> Dict[str, Any] | None:
        mapping = RULE_ACTION_MAP.get(finding.rule_id)
        if not mapping:
            return None

        savings = round(resource.cost_monthly * mapping["savings_factor"], 2)
        priority = mapping["priority_fn"](resource.cost_monthly)
        confidence = self._confidence(finding, resource)

        action = {
            "action_type": mapping["action_type"],
            "description": self._action_description(mapping["action_type"], resource),
            "estimated_savings_monthly": savings,
            "risk_level": mapping["risk"],
            "reversible": mapping["reversible"],
            "execution_params": self._execution_params(mapping["action_type"], resource),
        }

        return {
            "id": str(uuid.uuid4()),
            "resource_id": resource.id,
            "resource_name": resource.name,
            "resource_type": resource.type,
            "region": resource.region,
            "priority": priority,
            "title": finding.title,
            "description": finding.description,
            "current_monthly_cost": resource.cost_monthly,
            "estimated_savings_monthly": savings,
            "confidence_score": confidence,
            "actions": [action],
            "reasoning": self._build_reasoning(finding, resource),
        }

    def _build_from_anomaly(self, anomaly, resource) -> Dict[str, Any] | None:
        return {
            "id": str(uuid.uuid4()),
            "resource_id": resource.id,
            "resource_name": resource.name,
            "resource_type": resource.type,
            "region": resource.region,
            "priority": "high",
            "title": f"Cost anomaly detected on {resource.name}",
            "description": anomaly["description"],
            "current_monthly_cost": resource.cost_monthly,
            "estimated_savings_monthly": 0.0,
            "confidence_score": min(1.0, anomaly["z_score"] / 4.0),
            "actions": [{
                "action_type": "schedule_shutdown",
                "description": "Investigate unexpected cost spike before taking action",
                "estimated_savings_monthly": 0.0,
                "risk_level": "low",
                "reversible": True,
                "execution_params": {},
            }],
            "reasoning": [anomaly["description"]],
        }

    def _confidence(self, finding, resource) -> float:
        base = 0.7
        cpu = resource.metrics.cpu_utilization or 0.0
        if finding.rule_id == "IDLE_INSTANCE" and cpu < 2.0:
            base = 0.95
        elif finding.rule_id == "UNDERUTILIZED_INSTANCE" and cpu < 10.0:
            base = 0.85
        return round(min(1.0, base), 2)

    def _action_description(self, action_type: str, resource) -> str:
        descriptions = {
            "stop_instance": f"Stop {resource.name} ({resource.instance_type})",
            "rightsize": (
                f"Resize {resource.name} from {resource.instance_type} "
                f"→ {DOWNSIZE_MAP.get(resource.instance_type or '', 'smaller type')}"
            ),
            "purchase_reserved": f"Purchase 1-year Reserved Instance for {resource.name}",
            "schedule_shutdown": f"Schedule off-hours shutdown for {resource.name}",
            "terminate_instance": f"Terminate {resource.name} (confirm no active usage)",
        }
        return descriptions.get(action_type, action_type.replace("_", " ").title())

    def _execution_params(self, action_type: str, resource) -> Dict[str, Any]:
        params: Dict[str, Any] = {"resource_id": resource.id, "region": resource.region}
        if action_type == "rightsize" and resource.instance_type:
            params["new_instance_type"] = DOWNSIZE_MAP.get(resource.instance_type, resource.instance_type)
        return params

    def _build_reasoning(self, finding, resource) -> List[str]:
        reasons = [finding.description]
        cpu = resource.metrics.cpu_utilization
        if cpu is not None:
            reasons.append(f"7-day average CPU utilization: {cpu:.1f}%")
        reasons.append(f"Current monthly cost: ${resource.cost_monthly:.0f}")
        if resource.instance_type:
            reasons.append(f"Instance type: {resource.instance_type}")
        return reasons
