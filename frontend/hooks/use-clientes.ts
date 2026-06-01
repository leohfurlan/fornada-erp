import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Cliente } from "@/types";

export function useClientes() {
  return useQuery<Cliente[]>({
    queryKey: ["clientes"],
    queryFn: async () => {
      const { data } = await api.get("/clientes");
      return data;
    },
  });
}

export function useCriarCliente() {
  const queryClient = useQueryClient();
  return useMutation<Cliente, Error, { nome: string; telefone?: string; observacoes?: string }>({
    mutationFn: async (payload) => {
      const { data } = await api.post("/clientes", payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clientes"] });
    },
  });
}
