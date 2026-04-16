"use client";

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import { formatCurrency } from "@/lib/utils";
import type { RecommendationSummary } from "@/lib/api";

interface SavingsSummaryProps {
  summary: RecommendationSummary;
}

const PRIORITY_COLORS: Record<string, string> = {
  critical: "#ef4444",
  high: "#f97316",
  medium: "#f59e0b",
  low: "#3b82f6",
};

export function SavingsSummary({ summary }: SavingsSummaryProps) {
  const data = [
    { name: "Critical", value: summary.critical, color: PRIORITY_COLORS.critical },
    { name: "High", value: summary.high, color: PRIORITY_COLORS.high },
    { name: "Medium", value: summary.medium, color: PRIORITY_COLORS.medium },
    { name: "Low", value: summary.low, color: PRIORITY_COLORS.low },
  ].filter(d => d.value > 0);

  return (
    <div className="rounded-xl border border-white/[0.06] bg-white/[0.03] p-5">
      <h3 className="mb-4 text-sm font-semibold text-slate-200">Savings Opportunity</h3>

      <div className="flex items-center gap-6">
        <div className="flex-shrink-0">
          <ResponsiveContainer width={100} height={100}>
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={30}
                outerRadius={46}
                dataKey="value"
                strokeWidth={0}
              >
                {data.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                formatter={(v, name) => [v, name]}
                contentStyle={{
                  background: "#0f172a",
                  border: "1px solid rgba(255,255,255,0.08)",
                  borderRadius: 8,
                  fontSize: 12,
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="flex-1">
          <div className="mb-3">
            <p className="text-2xl font-bold text-green-400">
              {formatCurrency(summary.total_potential_savings_monthly)}/mo
            </p>
            <p className="text-xs text-slate-500">
              {formatCurrency(summary.total_potential_savings_monthly * 12)}/yr potential savings
            </p>
          </div>
          <div className="space-y-1.5">
            {data.map(d => (
              <div key={d.name} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ backgroundColor: d.color }}
                  />
                  <span className="text-xs text-slate-400">{d.name}</span>
                </div>
                <span className="text-xs font-medium text-slate-300">{d.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {summary.pending_approval > 0 && (
        <div className="mt-4 rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2">
          <p className="text-xs text-amber-400">
            {summary.pending_approval} recommendation
            {summary.pending_approval !== 1 ? "s" : ""} pending approval
          </p>
        </div>
      )}
    </div>
  );
}
