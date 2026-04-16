from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from enum import Enum
from datetime import datetime


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(str, Enum):
    COST_SPIKE = "cost_spike"
    IDLE_RESOURCE = "idle_resource"
    BUDGET_EXCEEDED = "budget_exceeded"
    ANOMALY_DETECTED = "anomaly_detected"
    RECOMMENDATION_READY = "recommendation_ready"
    ACTION_EXECUTED = "action_executed"
    ACTION_FAILED = "action_failed"


class Alert(BaseModel):
    id: str
    type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    resource_id: Optional[str] = None
    resource_name: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    acknowledged: bool = False
    slack_sent: bool = False
    slack_ts: Optional[str] = None

    class Config:
        use_enum_values = True
