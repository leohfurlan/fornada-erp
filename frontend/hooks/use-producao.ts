import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { OrdemProducao, StatusOP } from "@/types";

interface FiltrosOP {
  status?: StatusOP;
  receita_id?: string;
  pedido_id?: string;
  data_de?: string;
  data_ate?: string;
}

export function useOrdensProducao(filtros: FiltrosOP = {}) {
  return useQuery<OrdemProducao[]>({
    queryKey: ["ordens-producao", filtros],
    queryFn: async () => {
      const { data } = await api.get("/producao/ordens", { params: filtros });
      return data;
    },
  });
}

export function useOrdemProducao(id: string) {
  return useQuery<OrdemProducao>({
    queryKey: ["ordens-producao", id],
    queryFn: async () => {
      const { data } = await api.get(`/producao/ordens/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useCriarOrdemProducao() {
  const queryClient = useQueryClient();
  return useMutation<OrdemProducao, Error, unknown>({
    mutationFn: async (payload) => {
      const { data } = await api.post("/producao/ordens", payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ordens-producao"] });
    },
  });
}

export function useMudarStatusOP(id: string) {
  const queryClient = useQueryClient();
  return useMutation<OrdemProducao, Error, { status: StatusOP; qtd_produzida?: number }>({
    mutationFn: async (payload) => {
      const { data } = await api.patch(`/producao/ordens/${id}/status`, payload);
      return data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["ordens-producao"] });
      queryClient.invalidateQueries({ queryKey: ["ingredientes"] });
      queryClient.invalidateQueries({ queryKey: ["estoque-pa"] });
      queryClient.setQueryData(["ordens-producao", id], data);
    },
  });
}

export function useDeletarOrdemProducao() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      await api.delete(`/producao/ordens/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ordens-producao"] });
    },
  });
}
