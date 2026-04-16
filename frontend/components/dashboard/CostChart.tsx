"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import type { ForecastPoint } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";

interface CostChartProps {
  data: ForecastPoint[];
  currentMonthly: number;
  forecastedMonthly: number;
  trendPercent: number;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  const pt = payload[0];
  return (
    <div className="rounded-lg border border-white/[0.08] bg-slate-900 px-3 py-2 shadow-xl">
      <p className="text-xs text-slate-400">{label}</p>
      <p className="text-sm font-semibold text-white">{formatCurrency(pt.value, 2)}</p>
      {pt.payload?.type === "forecast" && (
        <p className="text-xs text-blue-400">Forecast</p>
      )}
    </div>
  );
};

export function CostChart({ data, currentMonthly, forecastedMonthly, trendPercent }: CostChartProps) {
  const today = new Date().toISOString().split("T")[0];
  const todayIndex = data.findIndex(d => d.date >= today);

  return (
    <div className="rounded-xl border border-white/[0.06] bg-white/[0.03] p-5">
      <div className="mb-5 flex items-start justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-200">Cost Forecast</h3>
          <p className="mt-0.5 text-xs text-slate-500">30-day history + 7-day projection</p>
        </div>
        <div className="text-right">
          <p className="text-xs text-slate-500">Forecasted</p>
          <p className="text-lg font-bold text-white">{formatCurrency(forecastedMonthly)}/mo</p>
          <p
            className={`text-xs font-medium ${
              trendPercent >= 0 ? "text-red-400" : "text-green-400"
            }`}
          >
            {trendPercent >= 0 ? "+" : ""}
            {trendPercent.toFixed(1)}% vs current
          </p>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={data} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="actualGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.25} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="forecastGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.25} />
              <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fill: "#64748b", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={d => d.slice(5)}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fill: "#64748b", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={v => `$${v}`}
            width={40}
          />
          <Tooltip content={<CustomTooltip />} />
          {todayIndex > 0 && (
            <ReferenceLine
              x={data[todayIndex]?.date}
              stroke="rgba(255,255,255,0.15)"
              strokeDasharray="4 4"
              label={{ value: "Today", fill: "#64748b", fontSize: 10 }}
            />
          )}
          <Area
            type="monotone"
            dataKey="cost"
            stroke="#3b82f6"
            strokeWidth={1.5}
            fill="url(#actualGrad)"
            dot={false}
            activeDot={{ r: 3, fill: "#3b82f6" }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
