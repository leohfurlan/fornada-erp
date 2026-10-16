import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { HistoricoReceita } from "@/components/shared/historico-receita";

const mocks = vi.hoisted(() => ({ query: vi.fn(), get: vi.fn() }));
vi.mock("@tanstack/react-query", () => ({ useQuery: mocks.query }));
vi.mock("@/lib/api", () => ({ api: { get: mocks.get } }));
beforeEach(() => { cleanup(); mocks.query.mockReset(); });

describe("histórico da receita", () => {
  it("exibe autoria, quantidades e textos salvos e pagina versões", () => {
    const item = { versao: 3, created_at: "2026-10-12T12:00:00Z", responsavel: "Editor QA", origem: "edicao",
      snapshot: { nome: "BOLO", categoria: "Bolo", rendimento: "2.5000", rendimento_unidade: "un",
        ingredientes: [{ nome: "Chocolate", quantidade: "0.1250", unidade: "kg" }], etapas: [],
        modo_preparo: "**Misture** suavemente 🍰", ficha_tecnica: { passos: [{ descricao: "Finalização", quantidade: "30", unidade: "g", instrucao: "Finalize com cuidado." }] } } };
    mocks.query.mockReturnValue({ data: Array.from({ length: 20 }, (_, n) => ({ ...item, versao: n + 1 })) });
    render(<HistoricoReceita id="recipe-1" />);
    expect(screen.getAllByText(/Editor QA/)).toHaveLength(20);
    expect(screen.getAllByText("0,125 kg — Chocolate")).toHaveLength(20);
    expect(screen.getAllByText("Misture")[0].tagName).toBe("STRONG");
    expect(screen.getAllByText("Finalize com cuidado.")).toHaveLength(20);
    fireEvent.click(screen.getByRole("button", { name: "Mais antigas" }));
    expect(mocks.query.mock.lastCall?.[0].queryKey).toEqual(["receita-versoes", "recipe-1", 1]);
  });
  it("informa erro de consulta", () => {
    mocks.query.mockReturnValue({ isError: true });
    render(<HistoricoReceita id="recipe-1" />);
    expect(screen.getByRole("alert")).toHaveTextContent("Não foi possível carregar o histórico.");
  });
});
