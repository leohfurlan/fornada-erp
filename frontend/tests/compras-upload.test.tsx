import { act, renderHook } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { expect, it } from "vitest";
import { api } from "@/lib/api";
import { useLerCompra } from "@/hooks/use-compras-comerciais";

it("envia a imagem como arquivo multipart através da transformação real do Axios", async () => {
  const previous = api.defaults.adapter;
  const file = new File(["image"], "cupom.jpeg", { type: "image/jpeg" });
  let recebeuArquivo = false;
  api.defaults.adapter = async (config) => {
    expect(config.data).toBeInstanceOf(FormData);
    expect(config.data.get("arquivo")).toEqual(file);
    expect(config.headers.getContentType()).toContain("multipart/form-data");
    recebeuArquivo = true;
    return { config, status: 200, statusText: "OK", headers: {}, data: { itens: [] } };
  };
  const cache = new QueryClient();
  try {
    const hook = renderHook(() => useLerCompra(), {
      wrapper: ({ children }) => <QueryClientProvider client={cache}>{children}</QueryClientProvider>,
    });
    await act(async () => { await hook.result.current.mutateAsync(file); });
    expect(recebeuArquivo).toBe(true);
    hook.unmount();
  } finally {
    api.defaults.adapter = previous;
    cache.clear();
  }
});
