import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Ingrediente, MovimentacaoEstoque } from "@/types";

export function useIngredientes() {
  return useQuery<Ingrediente[]>({
    queryKey: ["ingredientes"],
    queryFn: async () => {
      const { data } = await api.get("/estoque/ingredientes");
      return data;
    },
  });
}

export function useIngrediente(id: string) {
  return useQuery<Ingrediente>({
    queryKey: ["ingredientes", id],
    queryFn: async () => {
      const { data } = await api.get(`/estoque/ingredientes/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useCriarIngrediente() {
  const queryClient = useQueryClient();
  return useMutation<Ingrediente, Error, unknown>({
    mutationFn: async (payload) => {
      const { data } = await api.post("/estoque/ingredientes", payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ingredientes"] });
    },
  });
}

export function useAtualizarIngrediente(id: string) {
  const queryClient = useQueryClient();
  return useMutation<Ingrediente, Error, unknown>({
    mutationFn: async (payload) => {
      const { data } = await api.patch(`/estoque/ingredientes/${id}`, payload);
      return data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["ingredientes"] });
      queryClient.setQueryData(["ingredientes", id], data);
    },
  });
}

export function useDeletarIngrediente() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      await api.delete(`/estoque/ingredientes/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ingredientes"] });
    },
  });
}

export function useMovimentacoesIngrediente(id: string) {
  return useQuery<MovimentacaoEstoque[]>({
    queryKey: ["ingredientes", id, "movimentacoes"],
    queryFn: async () => {
      const { data } = await api.get(`/estoque/ingredientes/${id}/movimentacoes`);
      return data;
    },
    enabled: !!id,
  });
}

export function useEntradaEstoque() {
  const queryClient = useQueryClient();
  return useMutation<Ingrediente, Error, unknown>({
    mutationFn: async (payload) => {
      const { data } = await api.post("/estoque/entrada", payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ingredientes"] });
    },
  });
}
