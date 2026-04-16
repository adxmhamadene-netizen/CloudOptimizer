const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API ${res.status}: ${err}`);
  }
  return res.json();
}

// ── Types ──────────────────────────────────────────────────────────────────

export type ResourceStatus = "running" | "stopped" | "idle" | "underutilized" | "optimized" | "unknown";
export type Priority = "critical" | "high" | "medium" | "low";

export interface ResourceMetrics {
  cpu_utilization: number | null;
  network_in_mbps: number | null;
  network_out_mbps: number | null;
  cpu_history: { timestamp: string; value: number }[];
  cost_history: { timestamp: string; value: number }[];
}

export interface Resource {
  id: string;
  name: string;
  type: string;
  region: string;
  account_id: string;
  status: ResourceStatus;
  instance_type: string | null;
  cost_monthly: number;
  cost_daily: number;
  usage_percent: number;
  metrics: ResourceMetrics;
  tags: Record<string, string>;
  launch_time: string | null;
}

export interface ResourceSummary {
  total_resources: number;
  total_monthly_cost: number;
  idle_resources: number;
  underutilized_resources: number;
  potential_monthly_savings: number;
  regions: string[];
  last_updated: string;
}

export interface CostByService {
  service: string;
  monthly_cost: number;
  daily_cost: number;
  trend_percent: number;
}

export interface RecommendedAction {
  action_type: string;
  description: string;
  estimated_savings_monthly: number;
  risk_level: string;
  reversible: boolean;
}

export interface Recommendation {
  id: string;
  resource_id: string;
  resource_name: string;
  resource_type: string;
  region: string;
  priority: Priority;
  title: string;
  description: string;
  current_monthly_cost: number;
  estimated_savings_monthly: number;
  confidence_score: number;
  actions: RecommendedAction[];
  reasoning: string[];
  approval_status: "pending" | "approved" | "rejected" | "executed" | "failed";
  created_at: string;
}

export interface RecommendationSummary {
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  total_potential_savings_monthly: number;
  pending_approval: number;
}

export interface ForecastPoint {
  date: string;
  cost: number;
  type: "actual" | "forecast";
}

export interface CostForecast {
  current_monthly: number;
  forecasted_monthly: number;
  trend_percent: number;
  forecast_days: number;
  generated_at: string;
  daily_series: ForecastPoint[];
  method: string;
}

// ── API calls ──────────────────────────────────────────────────────────────

export const api = {
  resources: {
    list: (params?: { status?: string; region?: string }) => {
      const qs = new URLSearchParams(params as Record<string, string>).toString();
      return request<Resource[]>(`/resources/${qs ? "?" + qs : ""}`);
    },
    get: (id: string) => request<Resource>(`/resources/${id}`),
    summary: () => request<ResourceSummary>("/resources/summary"),
    costByService: () => request<CostByService[]>("/resources/cost-by-service"),
  },
  recommendations: {
    list: (params?: { priority?: string; status?: string }) => {
      const qs = new URLSearchParams(params as Record<string, string>).toString();
      return request<Recommendation[]>(`/recommendations/${qs ? "?" + qs : ""}`);
    },
    summary: () => request<RecommendationSummary>("/recommendations/summary"),
    get: (id: string) => request<Recommendation>(`/recommendations/${id}`),
    approve: (id: string, approved: boolean, approver: string) =>
      request<Recommendation>(`/recommendations/${id}/approve`, {
        method: "POST",
        body: JSON.stringify({ recommendation_id: id, approved, approver }),
      }),
    analyze: () =>
      request<Record<string, unknown>>("/recommendations/analyze", {
        method: "POST",
        body: JSON.stringify({ force_refresh: true }),
      }),
  },
  forecast: {
    get: () => request<CostForecast>("/forecast/"),
    anomalies: () => request<unknown[]>("/forecast/anomalies"),
  },
};
