import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { EstoquePA, MovimentacaoEstoquePA } from "@/types";

export function useEstoquePA() {
  return useQuery<EstoquePA[]>({
    queryKey: ["estoque-pa"],
    queryFn: async () => {
      const { data } = await api.get("/estoque-pa");
      return data;
    },
  });
}

export function useSaldoPA(receitaId: string) {
  return useQuery<EstoquePA>({
    queryKey: ["estoque-pa", receitaId],
    queryFn: async () => {
      const { data } = await api.get(`/estoque-pa/${receitaId}`);
      return data;
    },
    enabled: !!receitaId,
  });
}

export function useAtualizarMinimaPA(receitaId: string) {
  const queryClient = useQueryClient();
  return useMutation<EstoquePA, Error, { qtd_minima: number }>({
    mutationFn: async (payload) => {
      const { data } = await api.patch(`/estoque-pa/${receitaId}`, payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["estoque-pa"] });
    },
  });
}

export function useMovimentacoesPA(receitaId: string) {
  return useQuery<MovimentacaoEstoquePA[]>({
    queryKey: ["estoque-pa", receitaId, "movimentacoes"],
    queryFn: async () => {
      const { data } = await api.get(`/estoque-pa/${receitaId}/movimentacoes`);
      return data;
    },
    enabled: !!receitaId,
  });
}
