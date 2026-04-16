from fastapi import APIRouter, Depends
from ..services.analyzer_service import AnalyzerService

router = APIRouter(prefix="/forecast", tags=["Forecast"])


def get_service() -> AnalyzerService:
    return AnalyzerService()


@router.get("/")
async def get_cost_forecast(service: AnalyzerService = Depends(get_service)):
    """30-day cost forecast with 7-day forward projection."""
    result = await service.run_analysis()
    return result.get("cost_forecast", {})


@router.get("/anomalies")
async def get_anomalies(service: AnalyzerService = Depends(get_service)):
    """List detected cost anomalies."""
    result = await service.run_analysis()
    return result.get("anomalies", [])
