"use client";

import { useState } from "react";
import { CheckCircle, XCircle, ChevronDown, ChevronUp, Zap } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { formatCurrency } from "@/lib/utils";
import { PRIORITY_CONFIG } from "@/lib/utils";
import type { Recommendation } from "@/lib/api";
import { api } from "@/lib/api";

interface RecommendationsPanelProps {
  recommendations: Recommendation[];
  onUpdate?: () => void;
}

export function RecommendationsPanel({ recommendations, onUpdate }: RecommendationsPanelProps) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [loading, setLoading] = useState<string | null>(null);

  const handleApprove = async (id: string, approved: boolean) => {
    setLoading(id);
    try {
      await api.recommendations.approve(id, approved, "dashboard_user");
      onUpdate?.();
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="rounded-xl border border-white/[0.06] bg-white/[0.03]">
      <div className="flex items-center gap-2 border-b border-white/[0.06] px-5 py-4">
        <Zap className="h-4 w-4 text-amber-400" />
        <h3 className="text-sm font-semibold text-slate-200">AI Recommendations</h3>
        <span className="ml-auto rounded-full bg-amber-400/10 px-2 py-0.5 text-xs font-medium text-amber-400">
          {recommendations.length}
        </span>
      </div>

      <div className="divide-y divide-white/[0.04]">
        {recommendations.length === 0 && (
          <div className="px-5 py-8 text-center text-sm text-slate-500">
            No recommendations — everything looks optimized.
          </div>
        )}
        {recommendations.map(rec => {
          const pc = PRIORITY_CONFIG[rec.priority] ?? PRIORITY_CONFIG.low;
          const isExpanded = expanded === rec.id;
          const isPending = rec.approval_status === "pending";

          return (
            <div key={rec.id} className="px-5 py-4">
              {/* Row header */}
              <div
                className="flex cursor-pointer items-start justify-between gap-4"
                onClick={() => setExpanded(isExpanded ? null : rec.id)}
              >
                <div className="flex min-w-0 flex-1 items-start gap-3">
                  <span className={`mt-1 h-2 w-2 flex-shrink-0 rounded-full ${pc.dot}`} />
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-slate-200">{rec.title}</p>
                    <p className="mt-0.5 text-xs text-slate-500">{rec.resource_name}</p>
                  </div>
                </div>
                <div className="flex flex-shrink-0 items-center gap-3">
                  <div className="text-right">
                    <p className="text-sm font-semibold text-green-400">
                      {formatCurrency(rec.estimated_savings_monthly)}/mo
                    </p>
                    <p className="text-xs text-slate-500">
                      {formatCurrency(rec.estimated_savings_monthly * 12)}/yr
                    </p>
                  </div>
                  <Badge color={pc.color} bg={pc.bg}>{pc.label}</Badge>
                  {isExpanded ? (
                    <ChevronUp className="h-4 w-4 text-slate-500" />
                  ) : (
                    <ChevronDown className="h-4 w-4 text-slate-500" />
                  )}
                </div>
              </div>

              {/* Expanded content */}
              {isExpanded && (
                <div className="mt-4 space-y-4 rounded-lg border border-white/[0.06] bg-white/[0.02] p-4">
                  <p className="text-xs leading-relaxed text-slate-400">{rec.description}</p>

                  {rec.reasoning.length > 0 && (
                    <div>
                      <p className="mb-1 text-xs font-medium uppercase tracking-wider text-slate-500">
                        Why
                      </p>
                      <ul className="space-y-1">
                        {rec.reasoning.map((r, i) => (
                          <li key={i} className="flex gap-2 text-xs text-slate-400">
                            <span className="mt-1 h-1 w-1 flex-shrink-0 rounded-full bg-slate-500" />
                            {r}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {rec.actions.length > 0 && (
                    <div>
                      <p className="mb-1 text-xs font-medium uppercase tracking-wider text-slate-500">
                        Actions
                      </p>
                      {rec.actions.map((action, i) => (
                        <div
                          key={i}
                          className="flex items-center justify-between rounded-md bg-white/[0.03] px-3 py-2"
                        >
                          <span className="text-xs text-slate-300">{action.description}</span>
                          <div className="flex items-center gap-2">
                            <span
                              className={`text-xs ${
                                action.risk_level === "low"
                                  ? "text-green-400"
                                  : action.risk_level === "medium"
                                  ? "text-amber-400"
                                  : "text-red-400"
                              }`}
                            >
                              {action.risk_level} risk
                            </span>
                            {action.reversible && (
                              <span className="text-xs text-slate-500">reversible</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="flex items-center justify-between pt-1">
                    <div className="flex items-center gap-4 text-xs text-slate-500">
                      <span>
                        Confidence:{" "}
                        <span className="text-slate-300">
                          {(rec.confidence_score * 100).toFixed(0)}%
                        </span>
                      </span>
                      <span>
                        Current:{" "}
                        <span className="text-slate-300">
                          {formatCurrency(rec.current_monthly_cost)}/mo
                        </span>
                      </span>
                    </div>

                    {isPending && (
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleApprove(rec.id, false)}
                          disabled={loading === rec.id}
                          className="flex items-center gap-1 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-1.5 text-xs font-medium text-red-400 transition hover:bg-red-500/20 disabled:opacity-50"
                        >
                          <XCircle className="h-3.5 w-3.5" /> Reject
                        </button>
                        <button
                          onClick={() => handleApprove(rec.id, true)}
                          disabled={loading === rec.id}
                          className="flex items-center gap-1 rounded-lg border border-green-500/30 bg-green-500/10 px-3 py-1.5 text-xs font-medium text-green-400 transition hover:bg-green-500/20 disabled:opacity-50"
                        >
                          <CheckCircle className="h-3.5 w-3.5" /> Approve
                        </button>
                      </div>
                    )}
                    {rec.approval_status !== "pending" && (
                      <Badge
                        color={rec.approval_status === "approved" ? "text-green-400" : "text-red-400"}
                        bg={rec.approval_status === "approved" ? "bg-green-400/10" : "bg-red-400/10"}
                      >
                        {rec.approval_status}
                      </Badge>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
