from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "CloudOptimizer"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # AWS
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_DEFAULT_REGION: str = "us-east-1"
    AWS_ACCOUNT_ID: Optional[str] = None

    # Slack
    SLACK_BOT_TOKEN: Optional[str] = None
    SLACK_SIGNING_SECRET: Optional[str] = None
    SLACK_ALERT_CHANNEL: str = "#cloud-alerts"
    SLACK_APPROVAL_CHANNEL: str = "#cloud-approvals"

    # AI/ML
    ANOMALY_THRESHOLD: float = 2.0       # std deviations
    IDLE_CPU_THRESHOLD: float = 5.0      # percent
    UNDERUTILIZED_CPU_THRESHOLD: float = 20.0
    IDLE_NETWORK_THRESHOLD: float = 1.0  # MB/hr
    COST_SPIKE_FACTOR: float = 1.5       # 50% above 7-day avg

    # Automation
    AUTO_EXECUTE_ACTIONS: bool = False
    REQUIRE_SLACK_APPROVAL: bool = True

    # Cache
    CACHE_TTL_SECONDS: int = 300

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
