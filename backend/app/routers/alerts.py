from fastapi import APIRouter, HTTPException, Request
from typing import List
import json
import hmac
import hashlib
import time
import logging

from ..models.alert import Alert, AlertType, AlertSeverity
from ..models.recommendation import ApprovalRequest
from ..services.analyzer_service import AnalyzerService
from ..config import settings

router = APIRouter(prefix="/alerts", tags=["Alerts"])
logger = logging.getLogger(__name__)

# In-memory alert store (swap for Redis/DB in production)
_alerts: List[Alert] = []


@router.get("/", response_model=List[Alert])
async def list_alerts(acknowledged: bool = False):
    """List all alerts, optionally filtering to unacknowledged only."""
    if not acknowledged:
        return [a for a in _alerts if not a.acknowledged]
    return _alerts


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """Mark an alert as acknowledged."""
    for alert in _alerts:
        if alert.id == alert_id:
            alert.acknowledged = True
            return {"status": "acknowledged"}
    raise HTTPException(status_code=404, detail="Alert not found")


@router.post("/slack/interactions")
async def handle_slack_interaction(request: Request):
    """
    Handles Slack interactive component callbacks (button clicks).
    Verifies the Slack signing secret before processing.
    """
    body_bytes = await request.body()

    # Verify Slack signature
    if settings.SLACK_SIGNING_SECRET:
        timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
        slack_sig = request.headers.get("X-Slack-Signature", "")
        age = abs(time.time() - int(timestamp or 0))
        if age > 300:
            raise HTTPException(status_code=400, detail="Request too old")

        sig_base = f"v0:{timestamp}:{body_bytes.decode()}"
        expected = "v0=" + hmac.new(
            settings.SLACK_SIGNING_SECRET.encode(),
            sig_base.encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, slack_sig):
            raise HTTPException(status_code=403, detail="Invalid signature")

    # Parse payload
    from urllib.parse import parse_qs
    parsed = parse_qs(body_bytes.decode())
    payload_str = parsed.get("payload", ["{}"])[0]
    payload = json.loads(payload_str)

    actions = payload.get("actions", [])
    user = payload.get("user", {}).get("name", "slack_user")

    service = AnalyzerService()
    for action in actions:
        action_id = action.get("action_id", "")
        value = json.loads(action.get("value", "{}"))
        rec_id = value.get("rec_id", "")
        approved = action_id == "approve_recommendation"

        if rec_id:
            await service.approve_recommendation(rec_id, approved, user)
            logger.info("Slack interaction: %s %s by %s", action_id, rec_id, user)

    return {"ok": True}
