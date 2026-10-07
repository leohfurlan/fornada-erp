import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import CompraPage from "@/components/shared/compra-comercial";
import { dataCompra, totalItem } from "@/lib/compras";

const mocks = vi.hoisted(() => ({ ler: vi.fn(), prever: vi.fn(), salvar: vi.fn(), reconhecer: vi.fn() }));
vi.mock("@/hooks/use-estoque", () => ({ useIngredientes: () => ({
  data: [{ id: "material", nome: "Chocolate branco", unidade: "kg", tipo: "ingrediente" }],
}) }));
vi.mock("@/hooks/use-compras-comerciais", () => ({
  useProdutosCompra: () => ({ data: [{ id: "produto", ingrediente_id: "material", nome: "Cobertura branca",
    marca: "Dr. Oetker", conteudo_embalagem: "1.01", unidade_conteudo: "kg", aprovado: true, revisao: 1 }] }),
  useFornecedoresCompra: () => ({ data: [{ id: "loja", nome: "Empório Ponto X" }] }),
  useLerCompra: () => ({ mutateAsync: mocks.ler, isPending: false }),
  usePreverCompra: () => ({ mutateAsync: mocks.prever, isPending: false }),
  useSalvarCompra: () => ({ mutateAsync: mocks.salvar, isPending: false }),
  useReconhecerCompra: () => ({ mutateAsync: mocks.reconhecer, isPending: false }),
}));
const observado = {
  indice: 0, descricao: "COBERTURA EM BARRA DR.OETKER 1,01KG",
  quantidade: "1", unidade: "un", preco_unitario: "35.99", preco_total: "35.99",
  desconto_item: null, marca_observada: "Dr. Oetker", fabricante_observado: null,
  variante_observada: null, conteudo_observado: "1.01", unidade_conteudo_observada: "kg",
  codigo_loja: null, gtin: null, gtin_confirmado: false, ingrediente_id: null, produto_id: null,
  nome_match: null, produto_revisao: null, reconhecimento: "nenhum", score: 0,
  explicacao: "Marca não comprova a variante.", pendencias: [], candidatos: [],
  vinculo_id: null, vinculo_revisao: null, tipo_sugerido: "ingrediente", unidade_sugerida: "kg",
};
beforeEach(() => {
  cleanup(); Object.values(mocks).forEach((mock) => mock.mockReset());
  mocks.ler.mockResolvedValue({ itens: [observado], estabelecimento: "EMPORIO PONTO X",
    fornecedor_id: "loja", data_compra: "2026-10-03", total_nota: "35.99", fonte: "gemma4" });
  mocks.prever.mockResolvedValue({ pode_confirmar: true, duplicidade: [], itens: [{
    indice: 0, nome_material: "Chocolate branco", quantidade_principal: "1.01",
    unidade_principal: "kg", custo_normalizado: "35.63366337", preco_total: "35.99", pendencias: [],
  }] });
  mocks.salvar.mockResolvedValue({ compra_id: "compra", total_selecionado: "35.99",
    ingredientes_atualizados: 1, ingredientes_criados: 0 });
});
async function foto() {
  render(<CompraPage />);
  fireEvent.change(screen.getByLabelText("Foto do cupom"), {
    target: { files: [new File(["receipt"], "cupom.jpeg", { type: "image/jpeg" })] },
  });
  await screen.findByText(observado.descricao);
}
function selecionar() {
  fireEvent.change(screen.getByLabelText("Material das receitas"), { target: { value: "material" } });
  fireEvent.change(screen.getByLabelText("Produto e embalagem comprados"), { target: { value: "produto" } });
}
describe("conferência comercial de compras", () => {
  it("cancelar ou ignorar o item não envia aprovação nem compra ao servidor", async () => {
    await foto(); selecionar();
    fireEvent.click(screen.getByText("Aprovar este produto para o material"));
    fireEvent.click(screen.getByText("Guardar esta descrição/código para próximas compras nesta loja"));
    fireEvent.click(screen.getByRole("checkbox", { name: "Incluir" }));
    expect(screen.getByRole("button", { name: "Conferir entrada no estoque" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Salvar compra" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "← Refazer ou cancelar" }));
    await screen.findByText("Entrada de compra");
    expect(mocks.prever).not.toHaveBeenCalled();
    expect(mocks.salvar).not.toHaveBeenCalled();
  });
  it("mantém produto desconhecido para revisão, sem criar material pela marca", async () => {
    await foto();
    expect(screen.getByLabelText("Material das receitas")).toHaveValue("");
    expect(screen.getByRole("button", { name: "Salvar compra" })).toBeDisabled();
    expect(screen.getByLabelText("Data da compra (deixe vazio se não identificada)")).toHaveValue("2026-10-03");
    expect(mocks.salvar).not.toHaveBeenCalled();
  });
  it("converte somente na prévia e reutiliza a chave após falha de rede", async () => {
    mocks.salvar.mockRejectedValueOnce(new Error("offline"));
    await foto(); selecionar();
    fireEvent.click(screen.getByText("Guardar esta descrição/código para próximas compras nesta loja"));
    fireEvent.click(screen.getByRole("button", { name: "Conferir entrada no estoque" }));
    await screen.findByText("Chocolate branco: 1,01 kg no estoque");
    fireEvent.click(screen.getByRole("button", { name: "Salvar compra" }));
    await screen.findByRole("alert");
    fireEvent.click(screen.getByRole("button", { name: "Salvar compra" }));
    await screen.findByText("Compra registrada!");
    expect(mocks.salvar).toHaveBeenCalledTimes(2);
    const [first, second] = mocks.salvar.mock.calls.map((call) => call[0]);
    expect(first.chave).toEqual(second.chave);
    expect(first.payload.itens[0]).toMatchObject({ ingrediente_id: "material", produto_id: "produto",
      quantidade: "1", unidade: "un", custo_unitario: "35.99", guardar_vinculo: true, criar_novo: false });
  });
  it("exige nova conferência ao editar quantidade e desliga aprovações em compra excepcional", async () => {
    await foto(); selecionar();
    fireEvent.click(screen.getByText("Aprovar este produto para o material"));
    fireEvent.click(screen.getByText("Aprovar esta loja para este produto"));
    fireEvent.click(screen.getByText("Guardar esta descrição/código para próximas compras nesta loja"));
    fireEvent.click(screen.getByText("Registrar apenas esta compra, sem aprovação permanente"));
    fireEvent.click(screen.getByRole("button", { name: "Conferir entrada no estoque" }));
    await screen.findByText("Chocolate branco: 1,01 kg no estoque");
    expect(mocks.prever.mock.calls[0][0].itens[0]).toMatchObject({
      aceitar_excecao: true, guardar_vinculo: false, aprovar_produto: false, aprovar_fornecedor: false });
    fireEvent.change(screen.getByLabelText("Quantidade na nota"), { target: { value: "2" } });
    expect(screen.getByRole("button", { name: "Salvar compra" })).toBeDisabled();
    expect(screen.getByLabelText("Total pago pelo item (R$)")).toHaveValue("71,98");
    expect(mocks.salvar).not.toHaveBeenCalled();
  });
  it("não aceita prévia atrasada para um formulário já alterado", async () => {
    let resolve: (value: unknown) => void = () => {};
    mocks.prever.mockImplementation(() => new Promise((done) => { resolve = done; }));
    await foto(); selecionar();
    fireEvent.click(screen.getByRole("button", { name: "Conferir entrada no estoque" }));
    fireEvent.change(screen.getByLabelText("Quantidade na nota"), { target: { value: "2" } });
    resolve({ pode_confirmar: true, itens: [], duplicidade: [] });
    await waitFor(() => expect(mocks.prever).toHaveBeenCalledOnce());
    expect(screen.getByRole("button", { name: "Salvar compra" })).toBeDisabled();
  });
});
describe("preços e datas", () => {
  it("calcula centavos com precisão e mantém data desconhecida explícita", () => {
    expect(totalItem("2", "35.99", "0")).toBe("71.98");
    expect(totalItem("2020", "0.03563366", "0")).toBe("71.98");
    expect(totalItem("1", "1.005", "0")).toBe("1.01");
    expect(totalItem("2", "35.99", "1.98")).toBe("70.00");
    expect(dataCompra(null)).toBe("Data não identificada");
  });
});
