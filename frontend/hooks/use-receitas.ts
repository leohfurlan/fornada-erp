import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Receita } from "@/types";

export function useReceitas() {
  return useQuery<Receita[]>({
    queryKey: ["receitas"],
    queryFn: async () => {
      const { data } = await api.get("/receitas");
      return data;
    },
  });
}

export function useReceita(id: string) {
  return useQuery<Receita>({
    queryKey: ["receitas", id],
    queryFn: async () => {
      const { data } = await api.get(`/receitas/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useCriarReceita() {
  const queryClient = useQueryClient();
  return useMutation<Receita, Error, unknown>({
    mutationFn: async (payload) => {
      const { data } = await api.post("/receitas", payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["receitas"] });
    },
  });
}

export function useAtualizarReceita(id: string) {
  const queryClient = useQueryClient();
  return useMutation<Receita, Error, unknown>({
    mutationFn: async (payload) => {
      const { data } = await api.patch(`/receitas/${id}`, payload);
      return data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["receitas"] });
      queryClient.setQueryData(["receitas", id], data);
    },
  });
}

export function useDuplicarReceita() {
  const queryClient = useQueryClient();
  return useMutation<Receita, Error, string>({
    mutationFn: async (id) => {
      const { data } = await api.post(`/receitas/${id}/duplicar`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["receitas"] });
    },
  });
}

export function useDeletarReceita() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      await api.delete(`/receitas/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["receitas"] });
    },
  });
}
