import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface PassoMontagem {
  descricao: string;
  tipo: "componente" | "ingrediente" | "embalagem" | "acabamento";
  quantidade: string;
  quantidade_minima: string | null;
  quantidade_maxima: string | null;
  unidade: "g" | "kg" | "ml" | "l" | "un";
  especificacao: string;
  instrucao: string;
  receita_base_id?: string | null;
  ingrediente_id?: string | null;
}
export interface FichaTecnica {
  descricao_produto: string;
  especificacao_final: string;
  passos: PassoMontagem[];
  revisao: number;
  composicao_ativa?: boolean;
}
export interface ConsumoComponente {
  tipo: "receita_base" | "material";
  id: string;
  nome: string;
  unidade: string;
  quantidade_por_fornada: string;
}
export function useConsumoComposicao(id: string) {
  return useQuery<ConsumoComponente[]>({ queryKey: ["consumo-composicao", id], queryFn: async () => (await api.get(`/receitas/${id}/consumo-composicao`)).data, enabled: !!id });
}
export function useFichaTecnica(id: string) {
  return useQuery<FichaTecnica>({
    queryKey: ["ficha-tecnica", id],
    queryFn: async () => (await api.get(`/receitas/${id}/ficha-tecnica`)).data,
    enabled: !!id,
  });
}
export function useSalvarFichaTecnica(id: string) {
  const client = useQueryClient();
  return useMutation<FichaTecnica, Error, FichaTecnica>({
    mutationFn: async (payload) => (await api.put(`/receitas/${id}/ficha-tecnica`, payload)).data,
    onSuccess: (data) => {
      client.setQueryData(["ficha-tecnica", id], data);
      client.invalidateQueries({ queryKey: ["receitas"] });
      client.invalidateQueries({ queryKey: ["consumo-composicao", id] });
    },
  });
}
