"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { TrendingUp, TrendingDown } from "lucide-react";
import type { CostByService } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";

interface ServiceBreakdownProps {
  services: CostByService[];
}

const COLORS = ["#3b82f6", "#8b5cf6", "#06b6d4", "#10b981", "#f59e0b", "#ef4444"];

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload as CostByService;
  return (
    <div className="rounded-lg border border-white/[0.08] bg-slate-900 px-3 py-2 shadow-xl">
      <p className="text-xs font-medium text-slate-200">{d.service}</p>
      <p className="text-sm font-bold text-white">{formatCurrency(d.monthly_cost)}/mo</p>
      <p
        className={`text-xs ${d.trend_percent >= 0 ? "text-red-400" : "text-green-400"}`}
      >
        {d.trend_percent >= 0 ? "+" : ""}
        {d.trend_percent.toFixed(1)}% trend
      </p>
    </div>
  );
};

export function ServiceBreakdown({ services }: ServiceBreakdownProps) {
  const sorted = [...services].sort((a, b) => b.monthly_cost - a.monthly_cost);
  const total = services.reduce((s, svc) => s + svc.monthly_cost, 0);

  return (
    <div className="rounded-xl border border-white/[0.06] bg-white/[0.03] p-5">
      <h3 className="mb-5 text-sm font-semibold text-slate-200">Cost by Service</h3>

      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={sorted} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="rgba(255,255,255,0.04)"
            vertical={false}
          />
          <XAxis
            dataKey="service"
            tick={{ fill: "#64748b", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={s => s.replace("Amazon ", "").replace("AWS ", "")}
          />
          <YAxis
            tick={{ fill: "#64748b", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={v => `$${v}`}
            width={40}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
          <Bar dataKey="monthly_cost" radius={[4, 4, 0, 0]}>
            {sorted.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <div className="mt-4 space-y-2">
        {sorted.slice(0, 4).map((svc, i) => (
          <div key={svc.service} className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span
                className="h-2 w-2 rounded-full"
                style={{ backgroundColor: COLORS[i % COLORS.length] }}
              />
              <span className="text-xs text-slate-400">
                {svc.service.replace("Amazon ", "").replace("AWS ", "")}
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs text-slate-500">
                {((svc.monthly_cost / total) * 100).toFixed(0)}%
              </span>
              <span className="text-xs font-medium text-slate-300">
                {formatCurrency(svc.monthly_cost)}
              </span>
              {svc.trend_percent !== 0 && (
                <span
                  className={`flex items-center gap-0.5 text-xs ${
                    svc.trend_percent > 0 ? "text-red-400" : "text-green-400"
                  }`}
                >
                  {svc.trend_percent > 0 ? (
                    <TrendingUp className="h-3 w-3" />
                  ) : (
                    <TrendingDown className="h-3 w-3" />
                  )}
                  {Math.abs(svc.trend_percent).toFixed(1)}%
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
