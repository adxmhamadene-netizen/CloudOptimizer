"use client";

import { useState } from "react";
import { ChevronUp, ChevronDown, Server, Database } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { formatCurrency, formatPercent, STATUS_CONFIG } from "@/lib/utils";
import type { Resource } from "@/lib/api";

interface ResourceTableProps {
  resources: Resource[];
  onSelect?: (resource: Resource) => void;
}

type SortKey = "name" | "cost_monthly" | "usage_percent" | "status" | "type";
type SortDir = "asc" | "desc";

const TYPE_ICON: Record<string, React.ReactNode> = {
  EC2: <Server className="h-3.5 w-3.5" />,
  RDS: <Database className="h-3.5 w-3.5" />,
};

export function ResourceTable({ resources, onSelect }: ResourceTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("cost_monthly");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [filter, setFilter] = useState("");

  const handleSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDir(d => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const filtered = resources.filter(
    r =>
      r.name.toLowerCase().includes(filter.toLowerCase()) ||
      r.type.toLowerCase().includes(filter.toLowerCase()) ||
      r.region.toLowerCase().includes(filter.toLowerCase())
  );

  const sorted = [...filtered].sort((a, b) => {
    const aVal = a[sortKey];
    const bVal = b[sortKey];
    const cmp =
      typeof aVal === "number" && typeof bVal === "number"
        ? aVal - bVal
        : String(aVal).localeCompare(String(bVal));
    return sortDir === "asc" ? cmp : -cmp;
  });

  const SortIcon = ({ col }: { col: SortKey }) =>
    sortKey === col ? (
      sortDir === "asc" ? (
        <ChevronUp className="h-3 w-3" />
      ) : (
        <ChevronDown className="h-3 w-3" />
      )
    ) : (
      <ChevronDown className="h-3 w-3 opacity-30" />
    );

  return (
    <div className="rounded-xl border border-white/[0.06] bg-white/[0.03]">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/[0.06] px-5 py-4">
        <h3 className="text-sm font-semibold text-slate-200">Resources</h3>
        <input
          type="text"
          placeholder="Filter resources..."
          value={filter}
          onChange={e => setFilter(e.target.value)}
          className="rounded-lg border border-white/[0.08] bg-white/[0.04] px-3 py-1.5 text-xs text-slate-300 placeholder-slate-500 outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20"
        />
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/[0.04]">
              {(
                [
                  ["name", "Name"],
                  ["type", "Type"],
                  ["cost_monthly", "Cost/mo"],
                  ["usage_percent", "Usage"],
                  ["status", "Status"],
                ] as [SortKey, string][]
              ).map(([key, label]) => (
                <th
                  key={key}
                  onClick={() => handleSort(key)}
                  className="cursor-pointer select-none px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500 hover:text-slate-300"
                >
                  <span className="flex items-center gap-1">
                    {label}
                    <SortIcon col={key} />
                  </span>
                </th>
              ))}
              <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                Region
              </th>
              <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                Instance
              </th>
              <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                Recommendation
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {sorted.map(resource => {
              const sc = STATUS_CONFIG[resource.status] ?? STATUS_CONFIG.unknown;
              const recommendation = getQuickRecommendation(resource);
              return (
                <tr
                  key={resource.id}
                  onClick={() => onSelect?.(resource)}
                  className="cursor-pointer transition-colors hover:bg-white/[0.02]"
                >
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-2">
                      <span className="text-slate-400">{TYPE_ICON[resource.type]}</span>
                      <span className="font-medium text-slate-200">{resource.name}</span>
                    </div>
                  </td>
                  <td className="px-5 py-3.5">
                    <span className="text-xs text-slate-400">{resource.type}</span>
                  </td>
                  <td className="px-5 py-3.5">
                    <span className="font-medium text-white">
                      {formatCurrency(resource.cost_monthly)}
                    </span>
                    <span className="ml-1 text-xs text-slate-500">
                      /{formatCurrency(resource.cost_daily, 2)} day
                    </span>
                  </td>
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-2">
                      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-white/[0.08]">
                        <div
                          className={usageBarColor(resource.usage_percent)}
                          style={{ width: `${Math.min(100, resource.usage_percent)}%` }}
                        />
                      </div>
                      <span className="text-xs text-slate-400">
                        {formatPercent(resource.usage_percent)}
                      </span>
                    </div>
                  </td>
                  <td className="px-5 py-3.5">
                    <Badge color={sc.color} bg={sc.bg}>
                      <span className={`h-1.5 w-1.5 rounded-full ${sc.color.replace("text-", "bg-")}`} />
                      {sc.label}
                    </Badge>
                  </td>
                  <td className="px-5 py-3.5">
                    <span className="text-xs text-slate-400">{resource.region}</span>
                  </td>
                  <td className="px-5 py-3.5">
                    <span className="text-xs text-slate-400">{resource.instance_type ?? "—"}</span>
                  </td>
                  <td className="max-w-xs px-5 py-3.5">
                    {recommendation ? (
                      <span className="text-xs text-amber-400">{recommendation}</span>
                    ) : (
                      <span className="text-xs text-slate-600">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="border-t border-white/[0.04] px-5 py-3">
        <span className="text-xs text-slate-500">
          {sorted.length} of {resources.length} resources
        </span>
      </div>
    </div>
  );
}

function usageBarColor(pct: number): string {
  const base = "h-full rounded-full transition-all ";
  if (pct < 5) return base + "bg-red-500";
  if (pct < 20) return base + "bg-amber-500";
  if (pct < 80) return base + "bg-green-500";
  return base + "bg-blue-500";
}

function getQuickRecommendation(r: Resource): string | null {
  if (r.status === "idle") return `Stop to save ${formatCurrency(r.cost_monthly)}/mo`;
  if (r.status === "underutilized") return `Rightsize to save ~${formatCurrency(r.cost_monthly * 0.45)}/mo`;
  return null;
}
