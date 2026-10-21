import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import EstoquePage from "@/app/(dashboard)/estoque/page";
import type { Ingrediente } from "@/types";

const mocks = vi.hoisted(() => ({ user: { id: "cook", tenant_id: "bakery" } }));
vi.mock("next/navigation", () => ({ useSearchParams: () => new URLSearchParams() }));
vi.mock("@/stores/use-auth-store", () => ({ useAuthStore: (selector: (state: unknown) => unknown) => selector({ usuario: mocks.user }) }));
vi.mock("@/hooks/use-estoque", () => ({ useIngredientes: () => ({ data: items, isLoading: false }) }));
vi.mock("@/components/shared/tabela-estoque-desktop", () => ({ TabelaEstoqueDesktop: () => null }));
vi.mock("@/components/shared/tab-estoque-pa", () => ({ TabEstoquePA: () => <p>Produtos prontos</p> }));
vi.mock("@/components/shared/ajustar-estoque-dialog", () => ({ AjustarEstoqueDialog: () => null }));
const base: Ingrediente = {
  id: "flour", tenant_id: "bakery", codigo: 1, tipo: "ingrediente", nome: "Farinha", unidade: "kg",
  estoque_atual: "5", quantidade_reservada: "0", saldo: "5", estoque_minimo: "1", custo_medio: "3",
  data_custo_atualizado: null, status_estoque: "ok", unidades_alternativas: [],
};
const items: Ingrediente[] = [base,
  { ...base, id: "box", codigo: 2, tipo: "embalagem", nome: "Caixa", status_estoque: "baixo" },
  { ...base, id: "bag", codigo: 3, tipo: "embalagem", nome: "Saco", status_estoque: "zerado" },
];
beforeEach(() => { sessionStorage.clear(); localStorage.clear(); mocks.user = { id: "cook", tenant_id: "bakery" }; });
afterEach(() => { cleanup(); vi.restoreAllMocks(); });
const search = () => screen.getByRole("textbox", { name: "Buscar por nome ou código" });
const openFilters = () => fireEvent.click(screen.getByRole("button", { name: /^Filtros/ }));

it("mantém busca fora do submenu e mostra as opções apenas ao abrir Filtros", () => {
  render(<EstoquePage />);
  expect(search()).toBeVisible();
  expect(screen.queryByLabelText("Tipo de item")).not.toBeInTheDocument();
  openFilters();
  expect(screen.getByLabelText("Tipo de item")).toBeVisible();
  expect(screen.getByLabelText("Situação do estoque")).toBeVisible();
  expect(screen.getByRole("combobox", { name: "Ordenar itens" })).toBeInTheDocument();
  openFilters();
  expect(screen.queryByLabelText("Tipo de item")).not.toBeInTheDocument();
});

it("recupera filtros e ordenação ao voltar da edição com uma nova montagem da página", async () => {
  const view = render(<EstoquePage />);
  openFilters();
  fireEvent.change(screen.getByLabelText("Tipo de item"), { target: { value: "embalagem" } });
  fireEvent.change(screen.getByLabelText("Situação do estoque"), { target: { value: "baixo" } });
  fireEvent.change(screen.getByRole("combobox", { name: "Ordenar itens" }), { target: { value: "nome" } });
  fireEvent.click(screen.getByRole("button", { name: "Inverter ordem" }));
  fireEvent.change(search(), { target: { value: "Caixa" } });
  fireEvent.click(screen.getByRole("button", { name: /Caixa/ }));
  expect(screen.getByRole("link", { name: "Editar" })).toHaveAttribute("href", "/estoque/box/editar");
  view.unmount();
  render(<EstoquePage />);
  await waitFor(() => expect(search()).toHaveValue("Caixa"));
  expect(screen.queryByText("Farinha")).not.toBeInTheDocument();
  openFilters();
  expect(screen.getByLabelText("Tipo de item")).toHaveValue("embalagem");
  expect(screen.getByLabelText("Situação do estoque")).toHaveValue("baixo");
  expect(screen.getByRole("combobox", { name: "Ordenar itens" })).toHaveValue("nome");
});

it("limpa só a busca pelo X circular e mantém os filtros aplicados", () => {
  render(<EstoquePage />);
  openFilters();
  fireEvent.change(screen.getByLabelText("Tipo de item"), { target: { value: "embalagem" } });
  fireEvent.change(search(), { target: { value: "Caixa" } });
  fireEvent.click(screen.getByRole("button", { name: "Limpar busca" }));
  expect(search()).toHaveValue("");
  expect(search()).toHaveFocus();
  expect(screen.getByLabelText("Tipo de item")).toHaveValue("embalagem");
  expect(screen.getByText("Saco")).toBeVisible();
  expect(screen.queryByText("Farinha")).not.toBeInTheDocument();
});

it("limpa filtros e ordenação sem apagar a busca e persiste a limpeza", async () => {
  const view = render(<EstoquePage />);
  openFilters();
  fireEvent.change(screen.getByLabelText("Tipo de item"), { target: { value: "embalagem" } });
  fireEvent.change(screen.getByLabelText("Situação do estoque"), { target: { value: "baixo" } });
  fireEvent.change(search(), { target: { value: "Caixa" } });
  openFilters();
  fireEvent.click(screen.getByRole("button", { name: "Limpar filtros" }));
  expect(search()).toHaveValue("Caixa");
  view.unmount(); render(<EstoquePage />);
  await waitFor(() => expect(search()).toHaveValue("Caixa"));
  openFilters();
  expect(screen.getByLabelText("Tipo de item")).toHaveValue("");
  expect(screen.getByLabelText("Situação do estoque")).toHaveValue("");
  expect(screen.getByRole("button", { name: "Limpar filtros" })).toBeDisabled();
});

it("não herda os filtros de outro usuário ou empresa", async () => {
  const view = render(<EstoquePage />);
  fireEvent.change(search(), { target: { value: "Caixa" } });
  mocks.user = { id: "other", tenant_id: "other-bakery" };
  view.rerender(<EstoquePage />);
  await waitFor(() => expect(search()).toHaveValue(""));
  mocks.user = { id: "cook", tenant_id: "bakery" };
  view.rerender(<EstoquePage />);
  await waitFor(() => expect(search()).toHaveValue("Caixa"));
});

it("continua funcionando se o armazenamento estiver corrompido ou bloqueado", () => {
  sessionStorage.setItem("fornada:estoque:filtros:v1:bakery:cook:propria", "{broken");
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("Blocked"); });
  render(<EstoquePage />);
  expect(search()).toHaveValue("");
  fireEvent.change(search(), { target: { value: "Caixa" } });
  expect(screen.getByText("Caixa")).toBeVisible();
  expect(screen.queryByText("Farinha")).not.toBeInTheDocument();
});
