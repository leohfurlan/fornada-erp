import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, cleanup } from "@testing-library/react";
import FichaPage from "@/app/(dashboard)/receitas/[id]/ficha-tecnica/page";

const mocks = vi.hoisted(() => ({ salvar: vi.fn() }));
vi.mock("next/navigation", () => ({ useParams: () => ({ id: "receita-1" }) }));
vi.mock("@/hooks/use-receitas", () => ({ useReceitas: () => ({ data: [] }) }));
vi.mock("@/hooks/use-estoque", () => ({ useIngredientes: () => ({ data: [] }) }));
vi.mock("@/hooks/use-ficha-tecnica", () => ({
  useConsumoComposicao: () => ({ data: [] }),
  useFichaTecnica: () => ({ data: { descricao_produto: "Sedução", especificacao_final: "Copo 300 ml", revisao: 2, passos: [
    { descricao: "Brigadeiro", tipo: "componente", quantidade: "30", unidade: "g", especificacao: "", instrucao: "" },
    { descricao: "Brownie", tipo: "componente", quantidade: "50", unidade: "g", especificacao: "", instrucao: "" },
    { descricao: "Brigadeiro", tipo: "componente", quantidade: "30", unidade: "g", especificacao: "", instrucao: "" },
  ] }, refetch: vi.fn() }),
  useSalvarFichaTecnica: () => ({ mutateAsync: mocks.salvar, isPending: false }),
}));
beforeEach(() => { cleanup(); mocks.salvar.mockReset(); });
describe("montagem", () => {
  it("salva a sequência reordenada preservando componentes repetidos e revisão", async () => {
    mocks.salvar.mockImplementation(async (data) => ({ ...data, revisao: 3 }));
    render(<FichaPage />);
    await screen.findByDisplayValue("Sedução");
    fireEvent.click(screen.getByRole("button", { name: "Subir etapa 2" }));
    fireEvent.click(screen.getByRole("button", { name: "Salvar ficha técnica" }));
    await waitFor(() => expect(mocks.salvar).toHaveBeenCalledOnce());
    const enviado = mocks.salvar.mock.calls[0][0];
    expect(enviado.passos.map((p: { descricao: string }) => p.descricao)).toEqual(["Brownie", "Brigadeiro", "Brigadeiro"]);
    expect(enviado.revisao).toBe(2);
    await screen.findByText("Ficha técnica salva.");
  });
  it("preserva o rascunho quando a gravação falha", async () => {
    mocks.salvar.mockRejectedValue(new Error("offline"));
    render(<FichaPage />);
    await screen.findByDisplayValue("Sedução");
    fireEvent.change(screen.getByLabelText("Descrição do produto"), { target: { value: "Minha alteração" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar ficha técnica" }));
    await screen.findByText(/Não foi possível salvar/);
    expect(screen.getByDisplayValue("Minha alteração")).toBeTruthy();
  });

  it("salva Markdown da descrição e montagem sem converter o conteúdo", async () => {
    mocks.salvar.mockImplementation(async (data) => ({ ...data, revisao: 3 }));
    render(<FichaPage />);
    await screen.findByDisplayValue("Sedução");
    const description = "## Sedução\n\n**Chocolate** com morango.";
    const instruction = "1. Coloque **brigadeiro**.\n2. Finalize com *morango*.";
    fireEvent.change(screen.getByLabelText("Descrição do produto"), { target: { value: description } });
    fireEvent.change(screen.getAllByLabelText("Instrução de montagem")[0], { target: { value: instruction } });
    fireEvent.click(screen.getByRole("button", { name: "Descrição do produto: prévia" }));
    expect(screen.getByRole("heading", { name: "Sedução" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Salvar ficha técnica" }));
    await waitFor(() => expect(mocks.salvar).toHaveBeenCalledOnce());
    expect(mocks.salvar.mock.calls[0][0].descricao_produto).toBe(description);
    expect(mocks.salvar.mock.calls[0][0].passos[0].instrucao).toBe(instruction);
  });
});
