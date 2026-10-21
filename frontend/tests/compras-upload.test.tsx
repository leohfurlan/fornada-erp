import { act, renderHook } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { expect, it } from "vitest";
import { api } from "@/lib/api";
import { useLerCompra } from "@/hooks/use-compras-comerciais";

it.each(["image/jpeg", "application/pdf"])("envia %s como arquivo multipart através da transformação real do Axios", async (type) => {
  const previous = api.defaults.adapter;
  const file = new File(["receipt"], type === "application/pdf" ? "cupom.pdf" : "cupom.jpeg", { type });
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
