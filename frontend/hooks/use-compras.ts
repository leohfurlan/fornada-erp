import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  ConfirmarCompraPayload,
  ConfirmarCompraResponse,
  ListaComprasResponse,
  OcrComprasResponse,
} from "@/types";

/** Envia a foto do cupom e recebe os itens extraídos com sugestão de match. */
export function useProcessarCupom() {
  return useMutation<OcrComprasResponse, Error, File>({
    mutationFn: async (arquivo) => {
      const form = new FormData();
      form.append("arquivo", arquivo);
      const { data } = await api.post("/compras/ocr", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return data;
    },
  });
}

/** Confirma a compra revisada: cria/atualiza ingredientes e recalcula custo médio. */
export function useConfirmarCompra() {
  const queryClient = useQueryClient();
  return useMutation<ConfirmarCompraResponse, Error, ConfirmarCompraPayload>({
    mutationFn: async (payload) => {
      const { data } = await api.post("/compras/confirmar", payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ingredientes"] });
      queryClient.invalidateQueries({ queryKey: ["lista-compras"] });
    },
  });
}

/** Lista inteligente de compras: ingredientes que atingiram o estoque mínimo. */
export function useListaCompras() {
  return useQuery<ListaComprasResponse>({
    queryKey: ["lista-compras"],
    queryFn: async () => {
      const { data } = await api.get("/compras/lista-sugerida");
      return data;
    },
  });
}
