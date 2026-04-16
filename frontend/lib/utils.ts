import { type ClassValue, clsx } from "clsx";
import type { Priority, ResourceStatus } from "./api";

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function formatCurrency(amount: number, decimals = 0): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(amount);
}

export function formatPercent(value: number, decimals = 1): string {
  return `${value.toFixed(decimals)}%`;
}

export const STATUS_CONFIG: Record<ResourceStatus, { label: string; color: string; bg: string }> = {
  running: { label: "Running", color: "text-green-400", bg: "bg-green-400/10" },
  stopped: { label: "Stopped", color: "text-slate-400", bg: "bg-slate-400/10" },
  idle: { label: "Idle", color: "text-red-400", bg: "bg-red-400/10" },
  underutilized: { label: "Underutilized", color: "text-amber-400", bg: "bg-amber-400/10" },
  optimized: { label: "Optimized", color: "text-blue-400", bg: "bg-blue-400/10" },
  unknown: { label: "Unknown", color: "text-slate-500", bg: "bg-slate-500/10" },
};

export const PRIORITY_CONFIG: Record<Priority, { label: string; color: string; bg: string; dot: string }> = {
  critical: { label: "Critical", color: "text-red-400", bg: "bg-red-400/10", dot: "bg-red-400" },
  high: { label: "High", color: "text-orange-400", bg: "bg-orange-400/10", dot: "bg-orange-400" },
  medium: { label: "Medium", color: "text-amber-400", bg: "bg-amber-400/10", dot: "bg-amber-400" },
  low: { label: "Low", color: "text-blue-400", bg: "bg-blue-400/10", dot: "bg-blue-400" },
};
