from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class ResourceType(str, Enum):
    EC2 = "EC2"
    RDS = "RDS"
    S3 = "S3"
    LAMBDA = "Lambda"
    ELB = "ELB"
    NAT_GATEWAY = "NAT Gateway"
    ELASTICACHE = "ElastiCache"
    REDSHIFT = "Redshift"


class ResourceStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    IDLE = "idle"
    UNDERUTILIZED = "underutilized"
    OPTIMIZED = "optimized"
    UNKNOWN = "unknown"


class MetricPoint(BaseModel):
    timestamp: datetime
    value: float


class ResourceMetrics(BaseModel):
    cpu_utilization: Optional[float] = None       # percent avg over 7 days
    memory_utilization: Optional[float] = None
    network_in_mbps: Optional[float] = None
    network_out_mbps: Optional[float] = None
    disk_read_ops: Optional[float] = None
    disk_write_ops: Optional[float] = None
    cpu_history: List[MetricPoint] = Field(default_factory=list)
    cost_history: List[MetricPoint] = Field(default_factory=list)


class Resource(BaseModel):
    id: str
    name: str
    type: ResourceType
    region: str
    account_id: str
    status: ResourceStatus
    instance_type: Optional[str] = None
    cost_monthly: float                            # USD
    cost_daily: float
    usage_percent: float                           # primary utilization metric
    metrics: ResourceMetrics = Field(default_factory=ResourceMetrics)
    tags: Dict[str, str] = Field(default_factory=dict)
    launch_time: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    raw_data: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class ResourceSummary(BaseModel):
    total_resources: int
    total_monthly_cost: float
    idle_resources: int
    underutilized_resources: int
    potential_monthly_savings: float
    regions: List[str]
    last_updated: datetime


class CostByService(BaseModel):
    service: str
    monthly_cost: float
    daily_cost: float
    trend_percent: float    # vs previous period
