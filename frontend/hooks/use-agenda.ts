import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { toDateKey } from "@/lib/agenda";
import type {
  AgendaItem,
  AtualizarAgendaItemPayload,
  CriarAgendaItemPayload,
  MoverAgendaItemPayload,
  ViewAgenda,
} from "@/types";

function paramsParaView(view: ViewAgenda, ref: Date) {
  if (view === "mes") {
    return { view, ano: ref.getFullYear(), mes: ref.getMonth() + 1 };
  }
  return { view, data: toDateKey(ref) };
}

/** Chave estável por período — para mês usamos ano-mês, senão a data. */
function chavePeriodo(view: ViewAgenda, ref: Date): string {
  if (view === "mes") return `${ref.getFullYear()}-${ref.getMonth() + 1}`;
  return toDateKey(ref);
}

export function useAgenda(view: ViewAgenda, dataReferencia: Date) {
  return useQuery<AgendaItem[]>({
    queryKey: ["agenda", view, chavePeriodo(view, dataReferencia)],
    queryFn: async () => {
      const { data } = await api.get("/agenda", {
        params: paramsParaView(view, dataReferencia),
      });
      return data;
    },
  });
}

export function useCriarAgendaItem() {
  const queryClient = useQueryClient();
  return useMutation<AgendaItem, Error, CriarAgendaItemPayload>({
    mutationFn: async (payload) => {
      const { data } = await api.post("/agenda", payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agenda"] });
    },
  });
}

export function useAtualizarAgendaItem(id: string) {
  const queryClient = useQueryClient();
  return useMutation<AgendaItem, Error, AtualizarAgendaItemPayload>({
    mutationFn: async (payload) => {
      const { data } = await api.patch(`/agenda/${id}`, payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agenda"] });
    },
  });
}

export function useMoverAgendaItem() {
  const queryClient = useQueryClient();
  return useMutation<
    AgendaItem,
    Error,
    { id: string; payload: MoverAgendaItemPayload }
  >({
    mutationFn: async ({ id, payload }) => {
      const { data } = await api.patch(`/agenda/${id}/mover`, payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agenda"] });
    },
  });
}

export function useMarcarConcluido() {
  const queryClient = useQueryClient();
  return useMutation<AgendaItem, Error, { id: string; concluido: boolean }>({
    mutationFn: async ({ id, concluido }) => {
      const { data } = await api.patch(`/agenda/${id}/concluir`, { concluido });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agenda"] });
    },
  });
}

export function useDeletarAgendaItem() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      await api.delete(`/agenda/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agenda"] });
    },
  });
}
