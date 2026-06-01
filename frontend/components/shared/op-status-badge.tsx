import { cn } from "@/lib/utils";
import type { StatusOP } from "@/types";

interface OpStatusBadgeProps {
  status: StatusOP;
  className?: string;
}

export const STATUS_OP_LABEL: Record<StatusOP, string> = {
  planejada: "Planejada",
  em_producao: "Em produção",
  finalizada: "Finalizada",
  cancelada: "Cancelada",
};

const statusConfig: Record<StatusOP, string> = {
  planejada: "bg-slate-100 text-slate-800",
  em_producao: "bg-amber-100 text-amber-800",
  finalizada: "bg-green-100 text-green-800",
  cancelada: "bg-red-100 text-red-800",
};

export function OpStatusBadge({ status, className }: OpStatusBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        statusConfig[status],
        className
      )}
    >
      {STATUS_OP_LABEL[status]}
    </span>
  );
}
