import { cn } from "@/lib/utils";
import type { StatusPedido } from "@/types";

interface PedidoStatusBadgeProps {
  status: StatusPedido;
  className?: string;
}

export const STATUS_LABEL: Record<StatusPedido, string> = {
  orcamento: "Orçamento",
  aprovado: "Aprovado",
  em_producao: "Em produção",
  finalizado: "Finalizado",
  entregue: "Entregue",
  cancelado: "Cancelado",
};

const statusConfig: Record<StatusPedido, string> = {
  orcamento: "bg-slate-100 text-slate-800",
  aprovado: "bg-blue-100 text-blue-800",
  em_producao: "bg-amber-100 text-amber-800",
  finalizado: "bg-purple-100 text-purple-800",
  entregue: "bg-green-100 text-green-800",
  cancelado: "bg-red-100 text-red-800",
};

export function PedidoStatusBadge({ status, className }: PedidoStatusBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        statusConfig[status],
        className
      )}
    >
      {STATUS_LABEL[status]}
    </span>
  );
}
