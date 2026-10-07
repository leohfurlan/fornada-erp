import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { CompraDetalhada, CompraResumo, CompraRevisada, FornecedorCompra, ItemObservado,
  LeituraCompra, Pagina, PreviaCompra, ProdutoCompra, ProdutoCriar, ResultadoCompra,
  VinculoCompra } from "@/types/compras";

/** Carrega páginas do catálogo sem esconder registros depois dos primeiros 200. */
async function catalogo<T>(path: string, params: Record<string, string | number | boolean | undefined>): Promise<T[]> {
  const itens: T[] = [];
  for (let offset = 0; ; offset += 200) {
    const { data } = await api.get<Pagina<T>>(path, { params: { ...params, offset, limit: 200 } });
    itens.push(...data.itens);
    if (itens.length >= data.total || data.itens.length === 0) return itens;
  }
}
export function useProdutosCompra(ingredienteId?: string) {
  return useQuery({ queryKey: ["produtos-compra", ingredienteId],
    queryFn: () => catalogo<ProdutoCompra>("/compras/produtos", { ingrediente_id: ingredienteId }) });
}
export function useFornecedoresCompra() {
  return useQuery({ queryKey: ["fornecedores-compra"],
    queryFn: () => catalogo<FornecedorCompra>("/compras/fornecedores", {}) });
}
export function useVinculosCompra() {
  return useQuery({ queryKey: ["vinculos-compra"],
    queryFn: () => catalogo<VinculoCompra>("/compras/vinculos", {}) });
}
export function useCatalogoCompra() {
  const cache = useQueryClient();
  return useMutation({
    mutationFn: async (action: {
      recurso: "produtos" | "fornecedores" | "vinculos"; id?: string;
      revisao?: number; remover?: boolean; dados?: ProdutoCriar | Record<string, unknown>;
    }) => {
      const path = "/compras/" + action.recurso + (action.id ? "/" + action.id : "");
      if (action.remover) {
        await api.delete(path, { params: { revisao: action.revisao } });
        return;
      }
      return action.id ? (await api.patch(path, action.dados)).data : (await api.post(path, action.dados)).data;
    },
    onSuccess: () => {
      cache.invalidateQueries({ queryKey: ["produtos-compra"] });
      cache.invalidateQueries({ queryKey: ["fornecedores-compra"] });
      cache.invalidateQueries({ queryKey: ["vinculos-compra"] });
    },
  });
}
export function useLerCompra() {
  return useMutation({ mutationFn: async (file: File) => {
    const body = new FormData();
    body.append("arquivo", file);
    return (await api.post<LeituraCompra>("/compras/v2/ocr", body,
      { headers: { "Content-Type": "multipart/form-data" } })).data;
  } });
}
export function useReconhecerCompra() {
  return useMutation({ mutationFn: async (payload: { fornecedor_id: string | null; itens: ItemObservado[] }) =>
    (await api.post<{ itens: LeituraCompra["itens"] }>("/compras/v2/reconhecer", payload)).data });
}
export function usePreverCompra() {
  return useMutation({ mutationFn: async (payload: CompraRevisada) =>
    (await api.post<PreviaCompra>("/compras/v2/prever", payload)).data });
}
export function useSalvarCompra() {
  const cache = useQueryClient();
  return useMutation({ mutationFn: async ({ payload, chave }: { payload: CompraRevisada; chave: string }) =>
    (await api.post<ResultadoCompra>("/compras/v2/confirmar", payload,
      { headers: { "Idempotency-Key": chave } })).data,
    onSuccess: () => {
      for (const key of ["ingredientes", "lista-compras", "compras-historico",
        "produtos-compra", "fornecedores-compra", "vinculos-compra"]) {
        cache.invalidateQueries({ queryKey: [key] });
      }
    },
  });
}
export function useHistoricoCompras(filtros: Record<string, string | number | undefined>) {
  return useQuery({ queryKey: ["compras-historico", filtros],
    queryFn: async () => (await api.get<Pagina<CompraResumo>>("/compras/historico", { params: filtros })).data });
}
export function useDetalheCompra(id: string) {
  return useQuery({ queryKey: ["compras-historico", id], enabled: !!id,
    queryFn: async () => (await api.get<CompraDetalhada>("/compras/historico/" + id)).data });
}
