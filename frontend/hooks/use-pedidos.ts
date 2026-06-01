import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Pedido, StatusPedido } from "@/types";

interface FiltrosPedidos {
  status?: StatusPedido;
  cliente_id?: string;
  data_de?: string;
  data_ate?: string;
}

export function usePedidos(filtros: FiltrosPedidos = {}) {
  return useQuery<Pedido[]>({
    queryKey: ["pedidos", filtros],
    queryFn: async () => {
      const { data } = await api.get("/pedidos", { params: filtros });
      return data;
    },
  });
}

export function usePedido(id: string) {
  return useQuery<Pedido>({
    queryKey: ["pedidos", id],
    queryFn: async () => {
      const { data } = await api.get(`/pedidos/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useCriarPedido() {
  const queryClient = useQueryClient();
  return useMutation<Pedido, Error, unknown>({
    mutationFn: async (payload) => {
      const { data } = await api.post("/pedidos", payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pedidos"] });
    },
  });
}

export function useAtualizarPedido(id: string) {
  const queryClient = useQueryClient();
  return useMutation<Pedido, Error, unknown>({
    mutationFn: async (payload) => {
      const { data } = await api.patch(`/pedidos/${id}`, payload);
      return data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["pedidos"] });
      queryClient.setQueryData(["pedidos", id], data);
    },
  });
}

export function useMudarStatusPedido(id: string) {
  const queryClient = useQueryClient();
  return useMutation<Pedido, Error, StatusPedido>({
    mutationFn: async (status) => {
      const { data } = await api.patch(`/pedidos/${id}/status`, { status });
      return data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["pedidos"] });
      queryClient.invalidateQueries({ queryKey: ["ingredientes"] });
      queryClient.invalidateQueries({ queryKey: ["estoque-pa"] });
      queryClient.setQueryData(["pedidos", id], data);
    },
  });
}

export function useDeletarPedido() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      await api.delete(`/pedidos/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pedidos"] });
    },
  });
}
