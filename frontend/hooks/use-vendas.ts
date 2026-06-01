import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { CanalVenda, Venda } from "@/types";

interface FiltrosVenda {
  canal?: CanalVenda;
  cliente_id?: string;
  data_de?: string;
  data_ate?: string;
}

export function useVendas(filtros: FiltrosVenda = {}) {
  return useQuery<Venda[]>({
    queryKey: ["vendas", filtros],
    queryFn: async () => {
      const { data } = await api.get("/vendas", { params: filtros });
      return data;
    },
  });
}

export function useVenda(id: string) {
  return useQuery<Venda>({
    queryKey: ["vendas", id],
    queryFn: async () => {
      const { data } = await api.get(`/vendas/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useCriarVenda() {
  const queryClient = useQueryClient();
  return useMutation<Venda, Error, unknown>({
    mutationFn: async (payload) => {
      const { data } = await api.post("/vendas", payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["vendas"] });
      queryClient.invalidateQueries({ queryKey: ["estoque-pa"] });
    },
  });
}

export function useCancelarVenda() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      await api.delete(`/vendas/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["vendas"] });
      queryClient.invalidateQueries({ queryKey: ["estoque-pa"] });
    },
  });
}
