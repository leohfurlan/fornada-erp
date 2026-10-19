"use client";

import { useEffect, useState } from "react";
import { useAuthStore } from "@/stores/use-auth-store";
import { getSupportSession } from "@/lib/admin-session";
import { TIPOS_PRODUTO } from "@/lib/unidades";

export type EstoqueSortKey = "codigo" | "nome" | "saldo" | "custo_medio" | "data_custo_atualizado";
export type EstoqueSortDir = "asc" | "desc";
export interface EstoqueFilters {
  busca: string;
  tipo: string;
  status: string;
  sortKey: EstoqueSortKey;
  sortDir: EstoqueSortDir;
}
const defaults: EstoqueFilters = { busca: "", tipo: "", status: "", sortKey: "codigo", sortDir: "asc" };
const sortKeys: EstoqueSortKey[] = ["codigo", "nome", "saldo", "custo_medio", "data_custo_atualizado"];

function restore(raw: string | null): EstoqueFilters {
  if (!raw) return defaults;
  const value = JSON.parse(raw) as Partial<EstoqueFilters> | null;
  if (!value || typeof value !== "object" || Array.isArray(value)) return defaults;
  return {
    busca: typeof value.busca === "string" ? value.busca : "",
    tipo: TIPOS_PRODUTO.some(item => item.value === value.tipo) ? value.tipo! : "",
    status: ["ok", "baixo", "critico", "zerado"].includes(value.status ?? "") ? value.status! : "",
    sortKey: sortKeys.includes(value.sortKey!) ? value.sortKey! : "codigo",
    sortDir: value.sortDir === "desc" ? "desc" : "asc",
  };
}

/** Keep list context on return from edit/history, scoped to the signed-in account. */
export function useEstoqueFilters() {
  const user = useAuthStore(state => state.usuario);
  const support = getSupportSession();
  const key = user ? `fornada:estoque:filtros:v1:${user.tenant_id}:${user.id}:${support?.id ?? "propria"}` : null;
  const [state, setState] = useState<{ owner: string | null; filters: EstoqueFilters }>({ owner: null, filters: defaults });

  useEffect(() => {
    if (!key) return;
    let filters = defaults;
    try { filters = restore(sessionStorage.getItem(key)); } catch { /* Corrupt or unavailable storage starts with defaults. */ }
    setState({ owner: key, filters });
  }, [key]);
  useEffect(() => {
    if (!key || state.owner !== key) return;
    try { sessionStorage.setItem(key, JSON.stringify(state.filters)); } catch { /* Filtering remains usable when storage is blocked. */ }
  }, [key, state]);

  const filters = state.owner === key ? state.filters : defaults;
  const update = (changes: Partial<EstoqueFilters>) => setState(current => ({
    owner: key, filters: { ...(current.owner === key ? current.filters : defaults), ...changes },
  }));
  const clear = () => update({ tipo: "", status: "", sortKey: "codigo", sortDir: "asc" });
  return { filters, update, clear };
}
