from fastapi import APIRouter, HTTPException, Depends, Body
from typing import List, Optional

from ..models.recommendation import (
    Recommendation, RecommendationSummary, ApprovalRequest, ExecutionResult
)
from ..services.analyzer_service import AnalyzerService

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


def get_service() -> AnalyzerService:
    return AnalyzerService()


@router.get("/", response_model=List[dict])
async def list_recommendations(
    priority: Optional[str] = None,
    status: Optional[str] = None,
    service: AnalyzerService = Depends(get_service),
):
    """Return all current cost-optimization recommendations."""
    result = await service.run_analysis()
    recs = result.get("recommendations", [])
    if priority:
        recs = [r for r in recs if r.get("priority") == priority]
    if status:
        recs = [r for r in recs if r.get("approval_status") == status]
    return recs


@router.get("/summary", response_model=dict)
async def get_recommendation_summary(service: AnalyzerService = Depends(get_service)):
    """High-level summary of recommendations and savings potential."""
    result = await service.run_analysis()
    recs = result.get("recommendations", [])
    return {
        "total": len(recs),
        "critical": sum(1 for r in recs if r.get("priority") == "critical"),
        "high": sum(1 for r in recs if r.get("priority") == "high"),
        "medium": sum(1 for r in recs if r.get("priority") == "medium"),
        "low": sum(1 for r in recs if r.get("priority") == "low"),
        "total_potential_savings_monthly": round(
            sum(r.get("estimated_savings_monthly", 0) for r in recs), 2
        ),
        "pending_approval": sum(
            1 for r in recs if r.get("approval_status") == "pending"
        ),
    }


@router.post("/analyze", response_model=dict)
async def trigger_analysis(
    force_refresh: bool = Body(True, embed=True),
    service: AnalyzerService = Depends(get_service),
):
    """Trigger a fresh analysis run against AWS."""
    result = await service.run_analysis(force_refresh=force_refresh)
    return result.get("summary", {})


@router.get("/{rec_id}", response_model=dict)
async def get_recommendation(rec_id: str, service: AnalyzerService = Depends(get_service)):
    """Get a single recommendation by ID."""
    rec = await service.get_recommendation(rec_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return rec.dict()


@router.post("/{rec_id}/approve", response_model=dict)
async def approve_recommendation(
    rec_id: str,
    body: ApprovalRequest,
    service: AnalyzerService = Depends(get_service),
):
    """Approve or reject a recommendation (triggers Slack update + optional auto-execution)."""
    if body.recommendation_id != rec_id:
        raise HTTPException(status_code=400, detail="ID mismatch in request body")
    rec = await service.approve_recommendation(
        rec_id, body.approved, body.approver, body.notes
    )
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return rec.dict()
