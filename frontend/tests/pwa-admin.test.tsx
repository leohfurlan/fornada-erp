import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PwaAdmin } from "@/components/shared/pwa-admin";
import { pwaTipos } from "@/lib/pwa";

const state = vi.hoisted(() => ({ get: vi.fn() }));
vi.mock("@/lib/api", () => ({ api: { get: state.get } }));
afterEach(cleanup);
describe("adesão administrativa", () => {
  it("mostra ausência de evidência e sinais independentes", async () => {
    const sinais: Record<string, { quantidade: number; ultimo_em: string | null }> = Object.fromEntries(pwaTipos.map((tipo) => [tipo, { quantidade: 0, ultimo_em: null }]));
    sinais.confirmacao_aceita = { quantidade: 1, ultimo_em: "2026-10-12T15:00:00Z" };
    state.get.mockResolvedValue({ data: { total: 1, items: [{ usuario_id: "one", nome: "Cliente", negocio: "Loja", email: "pwa@example.invalid", sinais }] } });
    render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><PwaAdmin q="" offset={0} /></QueryClientProvider>);
    expect(await screen.findByText("Cliente · Loja")).toBeInTheDocument();
    expect(screen.getByText("Sem confirmação de instalação ou uso pelo aplicativo.")).toBeInTheDocument();
    expect(screen.getByText("Aceitou instalar")).toBeInTheDocument();
    expect(screen.getByText("Acessou pelo aplicativo")).toBeInTheDocument();
  });
});
