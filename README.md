# CloudOptimizer

AI-native cloud cost optimization platform. Analyzes your AWS infrastructure in real time, surfaces idle/underutilized resources, forecasts spend, and sends actionable recommendations to Slack for one-click approval.

## Features

- **Resource discovery** — EC2, RDS, S3, Lambda pulled via AWS APIs
- **AI analysis** — anomaly detection, idle/underutilized flagging, cost-spike alerts
- **Forecasting** — 30-day spend projections per service
- **Slack integration** — alerts to `#cloud-alerts`, approval workflow in `#cloud-approvals`
- **Mock mode** — runs fully without AWS credentials (rich demo data out of the box)

## Quick Start

### 1. Clone & configure

```bash
git clone https://github.com/craftlord659/CloudOptimizer.git
cd CloudOptimizer
cp .env.example .env
```

Edit `.env` and fill in your credentials (see sections below). You can leave both AWS and Slack blank to run in mock/demo mode.

### 2. Run with Docker Compose (recommended)

```bash
docker compose up --build
```

| Service  | URL                          |
|----------|------------------------------|
| Frontend | http://localhost:3000        |
| Backend  | http://localhost:8000        |
| API docs | http://localhost:8000/docs   |

### 3. Run locally (dev)

**Prerequisites:** Python 3.11+, Node 18+

```bash
# Install Python deps
pip install -r backend/requirements.txt

# Install frontend deps
cd frontend && npm install && cd ..

# Start both services
./start-dev.sh
```

---

## AWS Credentials

AWS credentials unlock live resource data. Without them the app uses realistic mock data.

### Option A — IAM User (simplest)

1. Open the [IAM console](https://console.aws.amazon.com/iam/) → **Users** → **Create user**
2. Attach the managed policy **ReadOnlyAccess** (or a custom policy — see below)
3. Under **Security credentials** → **Create access key** → choose *Application running outside AWS*
4. Copy the key pair into `.env`:

```env
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=wJalr...
AWS_DEFAULT_REGION=us-east-1   # your primary region
AWS_ACCOUNT_ID=123456789012    # 12-digit account ID
```

### Option B — IAM Role (EC2 / ECS / Lambda)

Attach the role to the compute instance; leave the key fields blank in `.env`. boto3 picks up the instance profile automatically.

### Minimum IAM permissions

If you prefer a least-privilege policy instead of `ReadOnlyAccess`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:Describe*",
        "rds:Describe*",
        "s3:ListAllMyBuckets",
        "s3:GetBucketLocation",
        "lambda:List*",
        "lambda:GetFunction",
        "cloudwatch:GetMetricStatistics",
        "cloudwatch:ListMetrics",
        "ce:GetCostAndUsage",
        "ce:GetCostForecast"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Slack Credentials

Slack integration sends cost alerts and surfaces an approval workflow for automated actions. Without it, alerts are logged to stdout only.

### Create a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → **From scratch**
2. Name it `CloudOptimizer`, pick your workspace

### Bot Token (`SLACK_BOT_TOKEN`)

1. In your app settings → **OAuth & Permissions**
2. Under **Bot Token Scopes** add:
   - `chat:write`
   - `chat:write.public`
   - `channels:read`
3. Click **Install to Workspace** → copy the **Bot User OAuth Token** (`xoxb-...`)

### Signing Secret (`SLACK_SIGNING_SECRET`)

1. In your app settings → **Basic Information** → **App Credentials**
2. Copy **Signing Secret**

### Add to `.env`

```env
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=abc123...
SLACK_ALERT_CHANNEL=#cloud-alerts       # channel for cost alerts
SLACK_APPROVAL_CHANNEL=#cloud-approvals # channel for action approvals
```

> **Tip:** Invite the bot to both channels with `/invite @CloudOptimizer` in Slack.

---

## Configuration Reference

All settings live in `.env` (backend reads them via `pydantic-settings`):

| Variable | Default | Description |
|---|---|---|
| `AWS_ACCESS_KEY_ID` | — | AWS access key (optional) |
| `AWS_SECRET_ACCESS_KEY` | — | AWS secret key (optional) |
| `AWS_DEFAULT_REGION` | `us-east-1` | Primary AWS region |
| `AWS_ACCOUNT_ID` | — | 12-digit AWS account ID |
| `SLACK_BOT_TOKEN` | — | Slack bot token (`xoxb-...`) |
| `SLACK_SIGNING_SECRET` | — | Slack app signing secret |
| `SLACK_ALERT_CHANNEL` | `#cloud-alerts` | Channel for alerts |
| `SLACK_APPROVAL_CHANNEL` | `#cloud-approvals` | Channel for approvals |
| `AUTO_EXECUTE_ACTIONS` | `false` | Auto-execute approved actions without human confirmation |
| `REQUIRE_SLACK_APPROVAL` | `true` | Gate automated actions behind Slack approval |
| `CACHE_TTL_SECONDS` | `300` | How long to cache AWS API responses |
| `IDLE_CPU_THRESHOLD` | `5.0` | CPU % below which an instance is considered idle |
| `UNDERUTILIZED_CPU_THRESHOLD` | `20.0` | CPU % below which an instance is considered underutilized |
| `ANOMALY_THRESHOLD` | `2.0` | Std deviations above mean to trigger a cost anomaly alert |
| `COST_SPIKE_FACTOR` | `1.5` | Multiplier above 7-day average to trigger a spike alert |

---

## Project Structure

```
CloudOptimizer/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── main.py       # App entry point
│   │   ├── config.py     # Settings (pydantic-settings)
│   │   ├── routers/      # API route handlers
│   │   ├── services/     # AWS, Slack, analyzer services
│   │   └── models/       # Pydantic models
│   └── requirements.txt
├── frontend/             # Next.js frontend
│   ├── app/              # App Router pages
│   └── lib/              # API client & utilities
├── ai/                   # AI/ML modules
│   ├── analyzer.py       # Cost analysis orchestrator
│   ├── anomaly_detector.py
│   ├── cost_predictor.py
│   ├── recommendations.py
│   └── rule_engine.py
├── docker-compose.yml
├── start-dev.sh          # Local dev launcher
└── .env.example          # Environment template
```

## License

MIT
