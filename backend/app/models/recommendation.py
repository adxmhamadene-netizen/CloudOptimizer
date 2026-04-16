from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class ActionType(str, Enum):
    STOP_INSTANCE = "stop_instance"
    TERMINATE_INSTANCE = "terminate_instance"
    RESIZE_INSTANCE = "resize_instance"
    PURCHASE_RESERVED = "purchase_reserved"
    DELETE_UNATTACHED_EBS = "delete_unattached_ebs"
    REMOVE_OLD_SNAPSHOTS = "remove_old_snapshots"
    DELETE_UNUSED_EIP = "delete_unused_eip"
    ENABLE_S3_LIFECYCLE = "enable_s3_lifecycle"
    SCHEDULE_SHUTDOWN = "schedule_shutdown"
    MIGRATE_TO_SPOT = "migrate_to_spot"
    RIGHTSIZE = "rightsize"


class Priority(str, Enum):
    CRITICAL = "critical"    # > $500/mo savings
    HIGH = "high"            # $100-500/mo
    MEDIUM = "medium"        # $20-100/mo
    LOW = "low"              # < $20/mo


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"


class RecommendedAction(BaseModel):
    action_type: ActionType
    description: str
    estimated_savings_monthly: float
    risk_level: str    # low / medium / high
    reversible: bool
    execution_params: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class Recommendation(BaseModel):
    id: str
    resource_id: str
    resource_name: str
    resource_type: str
    region: str
    priority: Priority
    title: str
    description: str
    current_monthly_cost: float
    estimated_savings_monthly: float
    confidence_score: float = Field(ge=0.0, le=1.0)
    actions: List[RecommendedAction] = Field(default_factory=list)
    reasoning: List[str] = Field(default_factory=list)   # human-readable rationale
    created_at: datetime = Field(default_factory=datetime.utcnow)
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    approved_by: Optional[str] = None
    executed_at: Optional[datetime] = None
    slack_message_ts: Optional[str] = None   # for approval thread

    class Config:
        use_enum_values = True


class RecommendationSummary(BaseModel):
    total: int
    critical: int
    high: int
    medium: int
    low: int
    total_potential_savings_monthly: float
    pending_approval: int


class ApprovalRequest(BaseModel):
    recommendation_id: str
    approved: bool
    approver: str
    notes: Optional[str] = None


class ExecutionResult(BaseModel):
    recommendation_id: str
    action_type: str
    success: bool
    message: str
    executed_at: datetime = Field(default_factory=datetime.utcnow)
    actual_savings: Optional[float] = None
