import { cn } from "@/lib/utils";
import type { Ingrediente } from "@/types";

interface EstoqueBadgeProps {
  status: Ingrediente["status_estoque"];
  className?: string;
}

const statusConfig = {
  ok: { label: "OK", className: "bg-green-100 text-green-800" },
  baixo: { label: "Estoque baixo", className: "bg-yellow-100 text-yellow-800" },
  critico: { label: "Crítico", className: "bg-orange-100 text-orange-800" },
  zerado: { label: "Zerado", className: "bg-red-100 text-red-800" },
};

export function EstoqueBadge({ status, className }: EstoqueBadgeProps) {
  const config = statusConfig[status];
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        config.className,
        className
      )}
    >
      {config.label}
    </span>
  );
}
