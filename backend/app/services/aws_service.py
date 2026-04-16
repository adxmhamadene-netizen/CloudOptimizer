"""
AWS service layer — wraps Cost Explorer and EC2 APIs.
Falls back to rich mock data when credentials are absent so the UI works out of the box.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from functools import lru_cache
import random
import uuid

from ..config import settings
from ..models.resource import (
    Resource, ResourceType, ResourceStatus, ResourceMetrics,
    MetricPoint, CostByService
)

logger = logging.getLogger(__name__)


def _boto3_available() -> bool:
    try:
        import boto3  # noqa: F401
        return True
    except ImportError:
        return False


def _get_boto3_client(service: str):
    import boto3
    kwargs: Dict[str, Any] = {"region_name": settings.AWS_DEFAULT_REGION}
    if settings.AWS_ACCESS_KEY_ID:
        kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
    return boto3.client(service, **kwargs)


# ---------------------------------------------------------------------------
# Mock data helpers
# ---------------------------------------------------------------------------

_INSTANCE_TYPES = ["t3.micro", "t3.small", "t3.medium", "t3.large",
                   "m5.large", "m5.xlarge", "m5.2xlarge",
                   "c5.large", "c5.xlarge", "r5.large"]

_REGIONS = ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]


def _make_cost_history(base: float, days: int = 30) -> List[MetricPoint]:
    now = datetime.utcnow()
    return [
        MetricPoint(
            timestamp=now - timedelta(days=days - i),
            value=round(base * random.uniform(0.8, 1.2), 4)
        )
        for i in range(days)
    ]


def _make_cpu_history(avg: float, days: int = 7) -> List[MetricPoint]:
    now = datetime.utcnow()
    return [
        MetricPoint(
            timestamp=now - timedelta(days=days - i),
            value=round(max(0.0, min(100.0, avg + random.gauss(0, avg * 0.15))), 2)
        )
        for i in range(days)
    ]


def _mock_resources() -> List[Resource]:
    random.seed(42)
    resources = []

    specs = [
        # (name, type, instance_type, cpu%, net_in, monthly_cost, status)
        ("web-prod-1",       ResourceType.EC2, "m5.xlarge",  72.0,  45.0, 180.0,  ResourceStatus.RUNNING),
        ("web-prod-2",       ResourceType.EC2, "m5.xlarge",  68.0,  42.0, 180.0,  ResourceStatus.RUNNING),
        ("api-server-prod",  ResourceType.EC2, "c5.2xlarge", 81.0,  80.0, 310.0,  ResourceStatus.RUNNING),
        ("data-processor",   ResourceType.EC2, "m5.2xlarge",  3.2,   1.0, 370.0,  ResourceStatus.IDLE),
        ("legacy-batch",     ResourceType.EC2, "m5.large",    2.1,   0.5,  92.0,  ResourceStatus.IDLE),
        ("staging-api",      ResourceType.EC2, "t3.large",   11.0,   5.0,  75.0,  ResourceStatus.UNDERUTILIZED),
        ("dev-sandbox",      ResourceType.EC2, "m5.xlarge",   7.5,   2.0, 180.0,  ResourceStatus.UNDERUTILIZED),
        ("analytics-worker", ResourceType.EC2, "r5.large",   14.0,   8.0, 145.0,  ResourceStatus.UNDERUTILIZED),
        ("ml-training",      ResourceType.EC2, "m5.2xlarge", 92.0, 120.0, 370.0,  ResourceStatus.RUNNING),
        ("cache-server",     ResourceType.EC2, "t3.medium",  18.0,  15.0,  38.0,  ResourceStatus.UNDERUTILIZED),
        ("rds-prod",         ResourceType.RDS, "db.r5.large", 45.0, 30.0, 280.0,  ResourceStatus.RUNNING),
        ("rds-staging",      ResourceType.RDS, "db.t3.medium", 8.0,  3.0,  55.0,  ResourceStatus.UNDERUTILIZED),
        ("rds-reporting",    ResourceType.RDS, "db.m5.large",  4.0,  1.5, 145.0,  ResourceStatus.IDLE),
    ]

    for i, (name, rtype, itype, cpu, net_in, cost_mo, status) in enumerate(specs):
        region = _REGIONS[i % len(_REGIONS)]
        daily = round(cost_mo / 30, 4)
        metrics = ResourceMetrics(
            cpu_utilization=cpu,
            network_in_mbps=net_in,
            network_out_mbps=round(net_in * 0.6, 2),
            cpu_history=_make_cpu_history(cpu),
            cost_history=_make_cost_history(daily),
        )
        resources.append(Resource(
            id=f"i-{uuid.uuid4().hex[:17]}",
            name=name,
            type=rtype,
            region=region,
            account_id=settings.AWS_ACCOUNT_ID or "123456789012",
            status=status,
            instance_type=itype,
            cost_monthly=cost_mo,
            cost_daily=daily,
            usage_percent=cpu,
            metrics=metrics,
            tags={"Name": name, "Env": "prod" if "prod" in name else "dev"},
            launch_time=datetime.utcnow() - timedelta(days=random.randint(10, 365)),
        ))

    return resources


def _mock_cost_by_service() -> List[CostByService]:
    return [
        CostByService(service="Amazon EC2",          monthly_cost=1740.0, daily_cost=58.0,  trend_percent=3.2),
        CostByService(service="Amazon RDS",          monthly_cost=480.0,  daily_cost=16.0,  trend_percent=-1.1),
        CostByService(service="Amazon S3",           monthly_cost=120.0,  daily_cost=4.0,   trend_percent=8.5),
        CostByService(service="AWS Lambda",          monthly_cost=45.0,   daily_cost=1.5,   trend_percent=-2.3),
        CostByService(service="Amazon CloudFront",   monthly_cost=90.0,   daily_cost=3.0,   trend_percent=1.8),
        CostByService(service="AWS Data Transfer",   monthly_cost=210.0,  daily_cost=7.0,   trend_percent=12.0),
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class AWSService:
    def __init__(self):
        self._use_mock = not _boto3_available() or not settings.AWS_ACCESS_KEY_ID
        if self._use_mock:
            logger.info("AWS credentials not configured — using mock data")

    async def get_resources(self) -> List[Resource]:
        if self._use_mock:
            return _mock_resources()
        return await self._fetch_live_resources()

    async def get_cost_by_service(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> List[CostByService]:
        if self._use_mock:
            return _mock_cost_by_service()
        return await self._fetch_live_cost_by_service(start_date, end_date)

    async def stop_ec2_instance(self, instance_id: str) -> Dict[str, Any]:
        if self._use_mock:
            return {"success": True, "instance_id": instance_id, "state": "stopping"}
        try:
            ec2 = _get_boto3_client("ec2")
            resp = ec2.stop_instances(InstanceIds=[instance_id])
            return {"success": True, "response": resp}
        except Exception as e:
            logger.error("Failed to stop %s: %s", instance_id, e)
            return {"success": False, "error": str(e)}

    async def resize_ec2_instance(
        self, instance_id: str, new_instance_type: str
    ) -> Dict[str, Any]:
        if self._use_mock:
            return {
                "success": True,
                "instance_id": instance_id,
                "new_type": new_instance_type
            }
        try:
            ec2 = _get_boto3_client("ec2")
            ec2.stop_instances(InstanceIds=[instance_id])
            ec2.get_waiter("instance_stopped").wait(InstanceIds=[instance_id])
            ec2.modify_instance_attribute(
                InstanceId=instance_id,
                InstanceType={"Value": new_instance_type}
            )
            ec2.start_instances(InstanceIds=[instance_id])
            return {"success": True, "new_type": new_instance_type}
        except Exception as e:
            logger.error("Failed to resize %s: %s", instance_id, e)
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Live AWS implementations
    # ------------------------------------------------------------------

    async def _fetch_live_resources(self) -> List[Resource]:
        """Fetch EC2 instances and their CloudWatch metrics."""
        try:
            ec2 = _get_boto3_client("ec2")
            cw = _get_boto3_client("cloudwatch")

            paginator = ec2.get_paginator("describe_instances")
            resources: List[Resource] = []

            for page in paginator.paginate():
                for reservation in page["Reservations"]:
                    for inst in reservation["Instances"]:
                        if inst["State"]["Name"] == "terminated":
                            continue
                        resource = await self._build_resource_from_ec2(inst, cw)
                        resources.append(resource)
            return resources
        except Exception as e:
            logger.error("Live EC2 fetch failed, falling back to mock: %s", e)
            return _mock_resources()

    async def _build_resource_from_ec2(
        self, inst: Dict[str, Any], cw_client: Any
    ) -> Resource:
        from datetime import timezone
        inst_id = inst["InstanceId"]
        tags = {t["Key"]: t["Value"] for t in inst.get("Tags", [])}
        name = tags.get("Name", inst_id)
        state = inst["State"]["Name"]

        cpu = await self._get_cloudwatch_metric(
            cw_client, inst_id, "CPUUtilization", "AWS/EC2", 7
        )

        status_map = {
            "running": ResourceStatus.RUNNING,
            "stopped": ResourceStatus.STOPPED,
        }
        raw_status = status_map.get(state, ResourceStatus.UNKNOWN)
        if raw_status == ResourceStatus.RUNNING and cpu < settings.IDLE_CPU_THRESHOLD:
            raw_status = ResourceStatus.IDLE
        elif raw_status == ResourceStatus.RUNNING and cpu < settings.UNDERUTILIZED_CPU_THRESHOLD:
            raw_status = ResourceStatus.UNDERUTILIZED

        cost = await self._estimate_ec2_cost(inst.get("InstanceType", ""))

        return Resource(
            id=inst_id,
            name=name,
            type=ResourceType.EC2,
            region=inst.get("Placement", {}).get("AvailabilityZone", settings.AWS_DEFAULT_REGION)[:-1],
            account_id=settings.AWS_ACCOUNT_ID or "unknown",
            status=raw_status,
            instance_type=inst.get("InstanceType"),
            cost_monthly=cost,
            cost_daily=round(cost / 30, 4),
            usage_percent=cpu,
            metrics=ResourceMetrics(cpu_utilization=cpu),
            tags=tags,
            launch_time=inst.get("LaunchTime"),
            raw_data=inst,
        )

    async def _get_cloudwatch_metric(
        self, cw_client, resource_id: str, metric: str,
        namespace: str, days: int
    ) -> float:
        try:
            end = datetime.utcnow()
            start = end - timedelta(days=days)
            resp = cw_client.get_metric_statistics(
                Namespace=namespace,
                MetricName=metric,
                Dimensions=[{"Name": "InstanceId", "Value": resource_id}],
                StartTime=start,
                EndTime=end,
                Period=86400,
                Statistics=["Average"],
            )
            points = resp.get("Datapoints", [])
            if not points:
                return 0.0
            return round(sum(p["Average"] for p in points) / len(points), 2)
        except Exception:
            return 0.0

    async def _estimate_ec2_cost(self, instance_type: str) -> float:
        # Simplified on-demand pricing lookup (us-east-1)
        pricing = {
            "t3.micro": 8.47, "t3.small": 16.93, "t3.medium": 33.87,
            "t3.large": 67.74, "m5.large": 87.60, "m5.xlarge": 175.20,
            "m5.2xlarge": 350.40, "c5.large": 77.00, "c5.xlarge": 154.00,
            "c5.2xlarge": 308.00, "r5.large": 114.00,
        }
        return pricing.get(instance_type, 100.0)

    async def _fetch_live_cost_by_service(
        self, start_date: Optional[str], end_date: Optional[str]
    ) -> List[CostByService]:
        try:
            ce = _get_boto3_client("ce")
            end = end_date or datetime.utcnow().strftime("%Y-%m-%d")
            start = start_date or (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")

            resp = ce.get_cost_and_usage(
                TimePeriod={"Start": start, "End": end},
                Granularity="MONTHLY",
                Metrics=["UnblendedCost"],
                GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
            )
            results = []
            for group in resp.get("ResultsByTime", [{}])[0].get("Groups", []):
                svc = group["Keys"][0]
                cost = float(group["Metrics"]["UnblendedCost"]["Amount"])
                results.append(CostByService(
                    service=svc,
                    monthly_cost=round(cost, 2),
                    daily_cost=round(cost / 30, 4),
                    trend_percent=0.0,
                ))
            return results
        except Exception as e:
            logger.error("Live cost fetch failed, falling back to mock: %s", e)
            return _mock_cost_by_service()
