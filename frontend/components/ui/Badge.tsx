import { cn } from "@/lib/utils";

interface BadgeProps {
  children: React.ReactNode;
  className?: string;
  color?: string;
  bg?: string;
}

export function Badge({ children, className, color, bg }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium",
        color,
        bg,
        className
      )}
    >
      {children}
    </span>
  );
}
