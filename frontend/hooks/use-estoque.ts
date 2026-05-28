import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Ingrediente } from "@/types";

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
