import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import ProducaoDetalhe from "@/app/(dashboard)/producao/[id]/page";

vi.mock("next/navigation", () => ({ useParams: () => ({ id: "op-1" }), useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/hooks/use-receitas", () => ({ useReceita: () => ({ data: undefined }) }));
vi.mock("@/hooks/use-producao", () => ({
  useOrdemProducao: () => ({ data: {
    id: "op-1", numero: 7, receita_id: "receita-da-op", nome_receita: "Bolo",
    status: "em_producao", qtd_planejada: "2", receita_rendimento: "10",
    receita_rendimento_unidade: "un", created_at: "2026-10-30T10:00:00Z", proximas_transicoes: [],
  } }),
  useMudarStatusOP: () => ({ error: null }),
  useDeletarOrdemProducao: () => ({ error: null }),
}));
afterEach(cleanup);

it("mostra no topo da OP o acesso à receita correspondente", () => {
  render(<ProducaoDetalhe />);
  const link = screen.getByRole("link", { name: "Ir para a receita" });
  expect(link).toHaveAttribute("href", "/receitas/receita-da-op");
  expect(link).toBeVisible();
  expect(link.compareDocumentPosition(screen.getByRole("heading", { name: "Bolo" })) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
});
