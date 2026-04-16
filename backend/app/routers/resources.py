from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from datetime import datetime

from ..models.resource import Resource, ResourceSummary, CostByService
from ..services.aws_service import AWSService
from ..services.analyzer_service import AnalyzerService

router = APIRouter(prefix="/resources", tags=["Resources"])


def get_aws_service() -> AWSService:
    return AWSService()


def get_analyzer_service() -> AnalyzerService:
    return AnalyzerService()


@router.get("/", response_model=List[Resource])
async def list_resources(
    status: Optional[str] = Query(None, description="Filter by status"),
    region: Optional[str] = Query(None, description="Filter by region"),
    resource_type: Optional[str] = Query(None, description="Filter by type"),
    aws: AWSService = Depends(get_aws_service),
):
    """List all cloud resources with their current utilization and cost."""
    resources = await aws.get_resources()
    if status:
        resources = [r for r in resources if r.status == status]
    if region:
        resources = [r for r in resources if r.region == region]
    if resource_type:
        resources = [r for r in resources if r.type == resource_type]
    return resources


@router.get("/summary", response_model=ResourceSummary)
async def get_resource_summary(aws: AWSService = Depends(get_aws_service)):
    """Aggregate summary of all resources and costs."""
    resources = await aws.get_resources()
    total_cost = sum(r.cost_monthly for r in resources)
    idle = sum(1 for r in resources if r.status == "idle")
    underutil = sum(1 for r in resources if r.status == "underutilized")
    regions = list({r.region for r in resources})

    # Rough savings estimate: stop idle (full cost) + rightsize underutilized (45%)
    savings = (
        sum(r.cost_monthly for r in resources if r.status == "idle")
        + sum(r.cost_monthly * 0.45 for r in resources if r.status == "underutilized")
    )

    return ResourceSummary(
        total_resources=len(resources),
        total_monthly_cost=round(total_cost, 2),
        idle_resources=idle,
        underutilized_resources=underutil,
        potential_monthly_savings=round(savings, 2),
        regions=regions,
        last_updated=datetime.utcnow(),
    )


@router.get("/cost-by-service", response_model=List[CostByService])
async def get_cost_by_service(aws: AWSService = Depends(get_aws_service)):
    """Cost breakdown by AWS service."""
    return await aws.get_cost_by_service()


@router.get("/{resource_id}", response_model=Resource)
async def get_resource(resource_id: str, aws: AWSService = Depends(get_aws_service)):
    """Get detailed info for a single resource."""
    resources = await aws.get_resources()
    for r in resources:
        if r.id == resource_id:
            return r
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail=f"Resource {resource_id} not found")
