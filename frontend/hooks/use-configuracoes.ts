import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface EtapaPadrao {
  id: string;
  nome: string;
  tipo_mao_obra: "direta" | "indireta";
  duracao_minutos_default: number;
}

export interface ConfiguracaoCusto {
  custo_operacional_mensal: string;
  horas_mensais: string;
  valor_hora: string;
  custo_por_hora: string;
}

// -------- Etapas padrão --------

export function useEtapasPadrao() {
  return useQuery<EtapaPadrao[]>({
    queryKey: ["etapas-padrao"],
    queryFn: async () => {
      const { data } = await api.get("/configuracoes/etapas");
      return data;
    },
  });
}

export function useCriarEtapaPadrao() {
  const qc = useQueryClient();
  return useMutation<EtapaPadrao, Error, Omit<EtapaPadrao, "id">>({
    mutationFn: async (payload) => {
      const { data } = await api.post("/configuracoes/etapas", payload);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["etapas-padrao"] }),
  });
}

export function useDeletarEtapaPadrao() {
  const qc = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      await api.delete(`/configuracoes/etapas/${id}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["etapas-padrao"] }),
  });
}

// -------- Configuração de custo --------

export function useConfiguracaoCusto() {
  return useQuery<ConfiguracaoCusto>({
    queryKey: ["configuracao-custo"],
    queryFn: async () => {
      const { data } = await api.get("/configuracoes/custos");
      return data;
    },
  });
}

export function useAtualizarConfiguracaoCusto() {
  const qc = useQueryClient();
  return useMutation<ConfiguracaoCusto, Error, { custo_operacional_mensal: number; horas_mensais: number; valor_hora: number }>({
    mutationFn: async (payload) => {
      const { data } = await api.put("/configuracoes/custos", payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["configuracao-custo"] });
      // Invalida receitas porque o custo recalcula com base nessa config
      qc.invalidateQueries({ queryKey: ["receitas"] });
    },
  });
}
