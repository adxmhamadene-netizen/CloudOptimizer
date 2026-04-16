"""
Rule-based findings engine.
Each rule returns a Finding dict:
  {resource_id, rule_id, title, description, severity, metadata}
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class Finding:
    resource_id: str
    resource_name: str
    resource_type: str
    rule_id: str
    title: str
    description: str
    severity: str          # critical / high / medium / low
    metadata: Dict[str, Any] = field(default_factory=dict)


Rule = Callable[[Any], List[Finding]]


class RuleEngine:
    """
    Evaluates a static set of cost-optimization rules against a resource list.
    Add new rules by defining a method prefixed with `_rule_` — they are
    auto-discovered and run in alphabetical order.
    """

    IDLE_CPU_THRESHOLD = 5.0
    UNDERUTILIZED_CPU_THRESHOLD = 20.0
    IDLE_NETWORK_THRESHOLD = 1.0           # MB/hr
    HIGH_COST_THRESHOLD = 200.0            # $/mo
    LONG_RUNNING_DAYS = 90

    def evaluate(self, resources: list) -> List[Finding]:
        findings: List[Finding] = []
        rules = [
            getattr(self, m)
            for m in sorted(dir(self))
            if m.startswith("_rule_")
        ]
        for resource in resources:
            for rule in rules:
                try:
                    findings.extend(rule(resource))
                except Exception as e:
                    logger.warning("Rule %s failed for %s: %s", rule.__name__, resource.id, e)
        return findings

    # ------------------------------------------------------------------
    # Rules
    # ------------------------------------------------------------------

    def _rule_01_idle_instance(self, r) -> List[Finding]:
        """Flag instances with CPU < 5% for 7 days."""
        cpu = r.metrics.cpu_utilization or 0.0
        if r.type in ("EC2", "RDS") and cpu < self.IDLE_CPU_THRESHOLD:
            return [Finding(
                resource_id=r.id,
                resource_name=r.name,
                resource_type=r.type,
                rule_id="IDLE_INSTANCE",
                title="Idle instance detected",
                description=(
                    f"{r.name} has averaged {cpu:.1f}% CPU over the last 7 days. "
                    "Consider stopping or terminating if no longer needed."
                ),
                severity="high" if r.cost_monthly > 100 else "medium",
                metadata={"cpu_avg": cpu, "cost_monthly": r.cost_monthly},
            )]
        return []

    def _rule_02_underutilized_instance(self, r) -> List[Finding]:
        """Flag instances with CPU 5-20% — candidates for rightsizing."""
        cpu = r.metrics.cpu_utilization or 0.0
        if (
            r.type in ("EC2", "RDS")
            and self.IDLE_CPU_THRESHOLD <= cpu < self.UNDERUTILIZED_CPU_THRESHOLD
        ):
            return [Finding(
                resource_id=r.id,
                resource_name=r.name,
                resource_type=r.type,
                rule_id="UNDERUTILIZED_INSTANCE",
                title="Underutilized instance — rightsize candidate",
                description=(
                    f"{r.name} averages {cpu:.1f}% CPU. "
                    "Downsizing the instance type could reduce cost by 30-50%."
                ),
                severity="medium",
                metadata={"cpu_avg": cpu, "instance_type": r.instance_type},
            )]
        return []

    def _rule_03_idle_network(self, r) -> List[Finding]:
        """Flag instances with near-zero network activity."""
        net = (r.metrics.network_in_mbps or 0.0) + (r.metrics.network_out_mbps or 0.0)
        cpu = r.metrics.cpu_utilization or 0.0
        if r.type == "EC2" and net < self.IDLE_NETWORK_THRESHOLD and cpu < self.UNDERUTILIZED_CPU_THRESHOLD:
            return [Finding(
                resource_id=r.id,
                resource_name=r.name,
                resource_type=r.type,
                rule_id="IDLE_NETWORK",
                title="Near-zero network activity",
                description=(
                    f"{r.name} has {net:.2f} MB/hr combined network I/O. "
                    "Low network + low CPU is a strong idle signal."
                ),
                severity="medium",
                metadata={"net_mbps": net},
            )]
        return []

    def _rule_04_high_cost_no_tags(self, r) -> List[Finding]:
        """Flag expensive resources missing cost-allocation tags."""
        if r.cost_monthly >= self.HIGH_COST_THRESHOLD and not r.tags.get("CostCenter"):
            return [Finding(
                resource_id=r.id,
                resource_name=r.name,
                resource_type=r.type,
                rule_id="MISSING_COST_TAG",
                title="High-cost resource missing CostCenter tag",
                description=(
                    f"{r.name} costs ${r.cost_monthly:.0f}/mo but has no CostCenter tag. "
                    "Add tags for accurate allocation and budget tracking."
                ),
                severity="low",
                metadata={"cost_monthly": r.cost_monthly},
            )]
        return []

    def _rule_05_reserved_instance_opportunity(self, r) -> List[Finding]:
        """Flag long-running on-demand instances that would benefit from Reserved pricing."""
        from datetime import datetime, timezone
        if not r.launch_time:
            return []
        try:
            launch = r.launch_time
            if launch.tzinfo is not None:
                launch = launch.replace(tzinfo=None)
            days_running = (datetime.utcnow() - launch).days
        except Exception:
            return []

        cpu = r.metrics.cpu_utilization or 0.0
        if (
            r.type == "EC2"
            and days_running >= self.LONG_RUNNING_DAYS
            and cpu >= self.UNDERUTILIZED_CPU_THRESHOLD
        ):
            savings_pct = 0.40   # ~40% RI discount
            return [Finding(
                resource_id=r.id,
                resource_name=r.name,
                resource_type=r.type,
                rule_id="RESERVED_INSTANCE_OPPORTUNITY",
                title="Reserved Instance opportunity",
                description=(
                    f"{r.name} has been running {days_running} days on-demand. "
                    f"A 1-year Reserved Instance saves ~40% (${r.cost_monthly * savings_pct:.0f}/mo)."
                ),
                severity="medium",
                metadata={"days_running": days_running, "savings_pct": savings_pct},
            )]
        return []
