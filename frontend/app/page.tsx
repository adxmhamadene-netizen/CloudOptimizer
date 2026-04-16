"use client";

import { useEffect, useState, useCallback } from "react";
import {
  DollarSign, Server, AlertTriangle, TrendingDown,
  RefreshCw, Bell, Settings, Cpu,
} from "lucide-react";

import { api } from "@/lib/api";
import type {
  Resource, Recommendation, ResourceSummary,
  CostByService, CostForecast, RecommendationSummary,
} from "@/lib/api";
import { formatCurrency } from "@/lib/utils";

import { StatCard } from "@/components/dashboard/StatCard";
import { ResourceTable } from "@/components/dashboard/ResourceTable";
import { RecommendationsPanel } from "@/components/dashboard/RecommendationsPanel";
import { CostChart } from "@/components/dashboard/CostChart";
import { ServiceBreakdown } from "@/components/dashboard/ServiceBreakdown";
import { SavingsSummary } from "@/components/dashboard/SavingsSummary";

export default function Dashboard() {
  const [resources, setResources] = useState<Resource[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [summary, setSummary] = useState<ResourceSummary | null>(null);
  const [recSummary, setRecSummary] = useState<RecommendationSummary | null>(null);
  const [services, setServices] = useState<CostByService[]>([]);
  const [forecast, setForecast] = useState<CostForecast | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "resources" | "recommendations">("overview");

  const loadData = useCallback(async () => {
    try {
      setError(null);
      const [res, recs, sum, recSum, svcs, fc] = await Promise.all([
        api.resources.list(),
        api.recommendations.list(),
        api.resources.summary(),
        api.recommendations.summary(),
        api.resources.costByService(),
        api.forecast.get(),
      ]);
      setResources(res);
      setRecommendations(recs as Recommendation[]);
      setSummary(sum);
      setRecSummary(recSum);
      setServices(svcs);
      setForecast(fc);
      setLastUpdated(new Date());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load data");
    }
  }, []);

  useEffect(() => {
    loadData().finally(() => setLoading(false));
  }, [loadData]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#080c14]">
        <div className="text-center">
          <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
          <p className="text-sm text-slate-400">Loading CloudOptimizer...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#080c14] text-slate-100">
      {/* Top nav */}
      <header className="sticky top-0 z-10 border-b border-white/[0.06] bg-[#080c14]/80 backdrop-blur">
        <div className="mx-auto flex max-w-screen-2xl items-center justify-between px-6 py-3">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500/20">
              <Cpu className="h-4 w-4 text-blue-400" />
            </div>
            <span className="text-sm font-semibold text-slate-100">CloudOptimizer</span>
            <span className="rounded-full border border-blue-500/20 bg-blue-500/10 px-2 py-0.5 text-xs text-blue-400">
              AI-native
            </span>
          </div>

          <nav className="flex gap-1">
            {(["overview", "resources", "recommendations"] as const).map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium capitalize transition ${
                  activeTab === tab
                    ? "bg-white/[0.08] text-slate-100"
                    : "text-slate-500 hover:text-slate-300"
                }`}
              >
                {tab}
              </button>
            ))}
          </nav>

          <div className="flex items-center gap-2">
            {lastUpdated && (
              <span className="text-xs text-slate-500">
                Updated {lastUpdated.toLocaleTimeString()}
              </span>
            )}
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="flex items-center gap-1.5 rounded-lg border border-white/[0.08] bg-white/[0.04] px-3 py-1.5 text-xs font-medium text-slate-300 transition hover:bg-white/[0.08] disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
              Refresh
            </button>
            <button className="rounded-lg border border-white/[0.08] bg-white/[0.04] p-1.5 text-slate-400 transition hover:text-slate-200">
              <Bell className="h-4 w-4" />
            </button>
            <button className="rounded-lg border border-white/[0.08] bg-white/[0.04] p-1.5 text-slate-400 transition hover:text-slate-200">
              <Settings className="h-4 w-4" />
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-screen-2xl px-6 py-6">
        {error && (
          <div className="mb-6 flex items-center gap-3 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3">
            <AlertTriangle className="h-4 w-4 flex-shrink-0 text-red-400" />
            <p className="text-sm text-red-400">{error}</p>
            <p className="text-xs text-red-500">
              (Backend may not be running — check console)
            </p>
          </div>
        )}

        {/* Stat cards */}
        <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="Monthly Spend"
            value={formatCurrency(summary?.total_monthly_cost ?? 0)}
            subtitle={`${summary?.total_resources ?? 0} resources`}
            icon={DollarSign}
            iconColor="text-blue-400"
            trend={
              forecast
                ? { value: forecast.trend_percent, label: "vs forecast" }
                : undefined
            }
          />
          <StatCard
            title="Potential Savings"
            value={formatCurrency(summary?.potential_monthly_savings ?? 0) + "/mo"}
            subtitle={formatCurrency((summary?.potential_monthly_savings ?? 0) * 12) + "/yr"}
            icon={TrendingDown}
            iconColor="text-green-400"
          />
          <StatCard
            title="Idle Resources"
            value={String(summary?.idle_resources ?? 0)}
            subtitle={`${summary?.underutilized_resources ?? 0} underutilized`}
            icon={Server}
            iconColor="text-amber-400"
          />
          <StatCard
            title="AI Recommendations"
            value={String(recSummary?.total ?? 0)}
            subtitle={`${recSummary?.pending_approval ?? 0} pending approval`}
            icon={AlertTriangle}
            iconColor="text-purple-400"
          />
        </div>

        {/* Overview tab */}
        {activeTab === "overview" && (
          <div className="space-y-6">
            <div className="grid gap-6 lg:grid-cols-3">
              <div className="lg:col-span-2">
                {forecast && (
                  <CostChart
                    data={forecast.daily_series}
                    currentMonthly={forecast.current_monthly}
                    forecastedMonthly={forecast.forecasted_monthly}
                    trendPercent={forecast.trend_percent}
                  />
                )}
              </div>
              <div>
                {recSummary && <SavingsSummary summary={recSummary} />}
              </div>
            </div>

            <div className="grid gap-6 lg:grid-cols-2">
              <ServiceBreakdown services={services} />
              <div className="rounded-xl border border-white/[0.06] bg-white/[0.03] p-5">
                <h3 className="mb-4 text-sm font-semibold text-slate-200">Top Cost Drivers</h3>
                <div className="space-y-3">
                  {resources
                    .sort((a, b) => b.cost_monthly - a.cost_monthly)
                    .slice(0, 5)
                    .map((r, i) => (
                      <div key={r.id} className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <span className="w-4 text-xs text-slate-500">{i + 1}</span>
                          <div>
                            <p className="text-xs font-medium text-slate-300">{r.name}</p>
                            <p className="text-xs text-slate-500">{r.instance_type} · {r.region}</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-xs font-semibold text-white">
                            {formatCurrency(r.cost_monthly)}/mo
                          </p>
                          <p className="text-xs text-slate-500">
                            {r.usage_percent.toFixed(0)}% used
                          </p>
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            </div>

            <RecommendationsPanel
              recommendations={recommendations.slice(0, 5)}
              onUpdate={handleRefresh}
            />
          </div>
        )}

        {activeTab === "resources" && (
          <ResourceTable resources={resources} />
        )}

        {activeTab === "recommendations" && (
          <RecommendationsPanel
            recommendations={recommendations}
            onUpdate={handleRefresh}
          />
        )}
      </main>
    </div>
  );
}
