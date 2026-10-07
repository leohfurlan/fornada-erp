import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ContaAdmin, SessaoSuporte } from "@/lib/admin-session";

export function useContasAdmin(q: string, offset: number, enabled: boolean) {
  return useQuery({
    queryKey: ["admin", "usuarios", q, offset],
    enabled,
    queryFn: async () => (await api.get<ContaAdmin[]>("/admin/usuarios", { params: { q, offset } })).data,
  });
}

export async function iniciarSuporte(usuario_id: string, motivo: string): Promise<Omit<SessaoSuporte, "operador_id">> {
  return (await api.post<Omit<SessaoSuporte, "operador_id">>("/admin/suporte", { usuario_id, motivo })).data;
}

export async function encerrarSuporte(id: string): Promise<void> {
  await api.delete(`/admin/suporte/${id}`);
}
