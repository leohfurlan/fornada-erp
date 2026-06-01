import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface AlertaEstoque {
  ingrediente_id: string;
  nome: string;
  estoque_atual: string;
  estoque_minimo: string;
  unidade: string;
  status: "baixo" | "critico" | "zerado";
}

export interface DashboardResumo {
  faturamento_semana: string;
  lucro_estimado_semana: string | null;
  total_vendas_semana: number;
  pedidos_em_aberto: number;
  ops_hoje: number;
  ops_em_producao: number;
  alertas_estoque: AlertaEstoque[];
  total_ingredientes_criticos: number;
}

export function useDashboardResumo() {
  return useQuery<DashboardResumo>({
    queryKey: ["dashboard-resumo"],
    queryFn: async () => {
      const { data } = await api.get("/dashboard/resumo");
      return data;
    },
    staleTime: 1000 * 60 * 2, // 2 minutos — dashboard não precisa ser realtime
    refetchOnWindowFocus: true,
  });
}
