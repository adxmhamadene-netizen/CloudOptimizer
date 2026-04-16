"""
Slack integration — sends alerts and handles interactive approval workflows.
"""
import logging
import json
from typing import Optional, Dict, Any

from ..config import settings
from ..models.recommendation import Recommendation, Priority
from ..models.alert import Alert, AlertSeverity

logger = logging.getLogger(__name__)


def _slack_available() -> bool:
    try:
        from slack_sdk import WebClient  # noqa: F401
        return bool(settings.SLACK_BOT_TOKEN)
    except ImportError:
        return False


def _get_client():
    from slack_sdk import WebClient
    return WebClient(token=settings.SLACK_BOT_TOKEN)


PRIORITY_EMOJI = {
    Priority.CRITICAL: ":red_circle:",
    Priority.HIGH: ":large_orange_circle:",
    Priority.MEDIUM: ":large_yellow_circle:",
    Priority.LOW: ":white_circle:",
}

SEVERITY_COLOR = {
    AlertSeverity.CRITICAL: "#FF0000",
    AlertSeverity.ERROR: "#FF6600",
    AlertSeverity.WARNING: "#FFC107",
    AlertSeverity.INFO: "#36A64F",
}


class SlackService:
    def __init__(self):
        self._available = _slack_available()
        if not self._available:
            logger.info("Slack not configured — alerts will be logged only")

    async def send_alert(self, alert: Alert) -> Optional[str]:
        message = self._build_alert_message(alert)
        if not self._available:
            logger.info("[SLACK ALERT] %s: %s", alert.severity, alert.title)
            return None
        try:
            client = _get_client()
            resp = client.chat_postMessage(
                channel=settings.SLACK_ALERT_CHANNEL,
                text=f"*{alert.title}*",
                attachments=[message],
            )
            return resp.get("ts")
        except Exception as e:
            logger.error("Slack alert failed: %s", e)
            return None

    async def send_approval_request(self, rec: Recommendation) -> Optional[str]:
        blocks = self._build_approval_blocks(rec)
        if not self._available:
            logger.info(
                "[SLACK APPROVAL REQUEST] %s — $%.0f/mo savings",
                rec.title, rec.estimated_savings_monthly
            )
            return None
        try:
            client = _get_client()
            resp = client.chat_postMessage(
                channel=settings.SLACK_APPROVAL_CHANNEL,
                text=f"Approval needed: {rec.title}",
                blocks=blocks,
            )
            return resp.get("ts")
        except Exception as e:
            logger.error("Slack approval request failed: %s", e)
            return None

    async def post_execution_result(
        self, rec: Recommendation, success: bool, message: str,
        thread_ts: Optional[str] = None
    ) -> None:
        emoji = ":white_check_mark:" if success else ":x:"
        text = f"{emoji} *{rec.title}* — {'executed successfully' if success else 'execution failed'}\n{message}"
        if not self._available:
            logger.info("[SLACK RESULT] %s", text)
            return
        try:
            client = _get_client()
            client.chat_postMessage(
                channel=settings.SLACK_APPROVAL_CHANNEL,
                text=text,
                thread_ts=thread_ts,
            )
        except Exception as e:
            logger.error("Slack result post failed: %s", e)

    async def update_approval_message(
        self, channel: str, ts: str, approved: bool, approver: str
    ) -> None:
        status = ":white_check_mark: Approved" if approved else ":x: Rejected"
        text = f"{status} by *{approver}*"
        if not self._available:
            logger.info("[SLACK UPDATE] %s", text)
            return
        try:
            client = _get_client()
            client.chat_postMessage(
                channel=channel,
                text=text,
                thread_ts=ts,
            )
        except Exception as e:
            logger.error("Slack update failed: %s", e)

    # ------------------------------------------------------------------
    # Message builders
    # ------------------------------------------------------------------

    def _build_alert_message(self, alert: Alert) -> Dict[str, Any]:
        color = SEVERITY_COLOR.get(AlertSeverity(alert.severity), "#808080")
        fields = [
            {"title": "Severity", "value": alert.severity.upper(), "short": True},
            {"title": "Type", "value": alert.type.replace("_", " ").title(), "short": True},
        ]
        if alert.resource_name:
            fields.append({"title": "Resource", "value": alert.resource_name, "short": True})
        return {
            "color": color,
            "title": alert.title,
            "text": alert.message,
            "fields": fields,
            "footer": "CloudOptimizer",
            "ts": int(alert.created_at.timestamp()),
        }

    def _build_approval_blocks(self, rec: Recommendation) -> list:
        emoji = PRIORITY_EMOJI.get(Priority(rec.priority), ":white_circle:")
        savings_text = f"*${rec.estimated_savings_monthly:,.0f}/mo* (${rec.estimated_savings_monthly * 12:,.0f}/yr)"
        actions_text = "\n".join(
            f"• {a.description}" for a in rec.actions
        ) or "See recommendation details"
        reasoning_text = "\n".join(f"• {r}" for r in rec.reasoning[:3])

        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} Cost Optimization Action Required",
                }
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{rec.title}*\n{rec.description}",
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Resource:*\n{rec.resource_name}"},
                    {"type": "mrkdwn", "text": f"*Type:*\n{rec.resource_type}"},
                    {"type": "mrkdwn", "text": f"*Current Cost:*\n${rec.current_monthly_cost:,.0f}/mo"},
                    {"type": "mrkdwn", "text": f"*Potential Savings:*\n{savings_text}"},
                    {"type": "mrkdwn", "text": f"*Priority:*\n{rec.priority.upper()}"},
                    {"type": "mrkdwn", "text": f"*Confidence:*\n{rec.confidence_score * 100:.0f}%"},
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Actions to be taken:*\n{actions_text}",
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Why:*\n{reasoning_text}",
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": ":white_check_mark: Approve"},
                        "style": "primary",
                        "value": json.dumps({"action": "approve", "rec_id": rec.id}),
                        "action_id": "approve_recommendation",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": ":x: Reject"},
                        "style": "danger",
                        "value": json.dumps({"action": "reject", "rec_id": rec.id}),
                        "action_id": "reject_recommendation",
                    },
                ],
            },
        ]
