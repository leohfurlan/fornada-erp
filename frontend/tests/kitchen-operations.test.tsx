import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { KitchenDayOverview, KitchenProductionQueue } from "@/components/shared/kitchen-operations";
import type { OrdemProducao } from "@/types";
import { toDateKey } from "@/lib/agenda";

const mocks = vi.hoisted(() => ({ get: vi.fn(), patch: vi.fn(), user: { id: "cook", tenant_id: "bakery" } }));
vi.mock("@/lib/api", () => ({ api: mocks }));
vi.mock("@/stores/use-auth-store", () => ({ useAuthStore: (selector: (state: unknown) => unknown) => selector({ usuario: mocks.user, isAuthenticated: true }) }));
beforeEach(() => {
  mocks.user = { id: "cook", tenant_id: "bakery" };
  mocks.get.mockResolvedValue({ data: [] });
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.resetAllMocks(); });
const base: OrdemProducao = {
  id: "op-1", tenant_id: "bakery", numero: 1, receita_id: "recipe-1", nome_receita: "Pão de queijo",
  receita_rendimento: "20", receita_rendimento_unidade: "un", pedido_id: null, pedido_numero: null,
  qtd_planejada: "2", qtd_produzida: null, status: "planejada", data_prevista: "2026-10-19", observacoes: null,
  created_at: "2026-10-19T10:00:00Z", updated_at: "2026-10-19T10:00:00Z", proximas_transicoes: ["em_producao", "cancelada"],
};
function mount(element: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return { client, ...render(<QueryClientProvider client={client}>{element}</QueryClientProvider>) };
}

it("prioriza OPs abertas por data e filtra por receita sem diferenciar acentos", async () => {
  mocks.get.mockResolvedValue({ data: [base, { ...base, id: "earlier", numero: 2, data_prevista: "2026-10-18" }, { ...base, id: "closed", numero: 3, status: "finalizada" }] });
  const open = vi.fn();
  mount(<KitchenProductionQueue search="pao" recipeOpen={false} disabled={false} onOpen={open} />);
  const cards = await screen.findAllByRole("article");
  expect(cards.map(card => card.getAttribute("aria-label"))).toEqual(["OP 2", "OP 1"]);
  fireEvent.click(screen.getByRole("button", { name: "Abrir receita da OP #1" }));
  expect(open).toHaveBeenCalledWith("recipe-1");
  expect(mocks.patch).not.toHaveBeenCalled();
});

it("inicia somente a OP escolhida após confirmar e bloqueia envio duplicado", async () => {
  mocks.get.mockResolvedValue({ data: [base] });
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  let resolve!: (value: unknown) => void;
  mocks.patch.mockImplementation(() => new Promise(done => { resolve = done; }));
  mount(<KitchenProductionQueue search="" recipeOpen={false} disabled={false} onOpen={vi.fn()} />);
  const start = await screen.findByRole("button", { name: "Iniciar OP #1" });
  fireEvent.click(start);
  expect(mocks.patch).not.toHaveBeenCalled();
  confirm.mockReturnValue(true);
  fireEvent.click(start); fireEvent.click(start);
  await waitFor(() => expect(mocks.patch).toHaveBeenCalledTimes(1));
  expect(mocks.patch).toHaveBeenCalledWith("/producao/ordens/op-1/status", { status: "em_producao" });
  await act(async () => resolve({ data: { ...base, status: "em_producao" } }));
  expect(await screen.findByText("OP #1 iniciada.")).toBeVisible();
});

it("finaliza com unidades reais em vez de fornadas e preserva formulário após recusa", async () => {
  mocks.get.mockResolvedValue({ data: [{ ...base, status: "em_producao", proximas_transicoes: ["finalizada"] }] });
  mocks.patch.mockRejectedValue({ response: { data: { detail: "Reserva insuficiente" } } });
  mount(<KitchenProductionQueue search="" recipeOpen={false} disabled={false} onOpen={vi.fn()} />);
  fireEvent.click(await screen.findByRole("button", { name: "Finalizar OP #1" }));
  const quantity = screen.getByRole("textbox", { name: "Quantidade produzida (un)" });
  expect(quantity).toHaveValue("40");
  fireEvent.change(quantity, { target: { value: "38,5" } });
  fireEvent.click(screen.getByRole("button", { name: "Confirmar finalização da OP #1" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Reserva insuficiente");
  expect(quantity).toHaveValue("38,5");
  expect(mocks.patch).toHaveBeenCalledWith("/producao/ordens/op-1/status", { status: "finalizada", qtd_produzida: 38.5 });
});

it("não reaproveita OPs em cache ao trocar de usuário ou tenant", async () => {
  mocks.get.mockResolvedValue({ data: [base] });
  const { rerender, client } = mount(<KitchenProductionQueue search="" recipeOpen={false} disabled={false} onOpen={vi.fn()} />);
  await screen.findByRole("article", { name: "OP 1" });
  mocks.user = { id: "other", tenant_id: "other-bakery" };
  mocks.get.mockResolvedValue({ data: [] });
  rerender(<QueryClientProvider client={client}><KitchenProductionQueue search="" recipeOpen={false} disabled={false} onOpen={vi.fn()} /></QueryClientProvider>);
  await screen.findByText("Nenhuma OP aberta.");
  expect(screen.queryByRole("article")).not.toBeInTheDocument();
});

it("mostra agenda de hoje e novos pedidos sem confirmar ou mudar status automaticamente", async () => {
  let incoming = false;
  mocks.get.mockImplementation(async (path: string) => {
    if (path === "/agenda") return { data: [{ id: "event", titulo: "Preparar massa", hora_inicio: "08:00:00", concluido: false }] };
    if (path === "/vendas") return { data: incoming ? [{ id: "sale", numero: 8, canal: "whatsapp", data_venda: "2026-10-19T10:00:00Z", itens: [{ id: "item", nome_receita: "Bolo de milho", quantidade: "2" }] }] : [] };
    return { data: { habilitado: true, pedidos: incoming ? [{ id: "ifood-order", ultimo_evento: "PLACED", snapshot: { displayId: "42", isTest: true, items: [{ name: "Brownie", quantity: "3" }] } }] : [] } };
  });
  const { client } = mount(<KitchenDayOverview recipeOpen={false} />);
  expect(await screen.findByText("08:00 · Preparar massa")).toBeVisible();
  expect(screen.getByRole("link", { name: "Abrir agenda" })).toHaveAttribute("href", "/agenda");
  expect(mocks.get).toHaveBeenCalledWith("/agenda", { params: { view: "dia", data: toDateKey(new Date()) } });
  incoming = true;
  await act(async () => { await client.invalidateQueries({ queryKey: ["cozinha-operacao"] }); });
  expect(await screen.findByText("iFood #42 · Pedido de teste")).toBeVisible();
  expect(screen.getByText("3 × Brownie")).toBeVisible();
  expect(screen.getByRole("link", { name: "WhatsApp · Venda #8" })).toBeVisible();
  expect(mocks.patch).not.toHaveBeenCalled();
});

it("mostra falhas de atualização e não as apresenta como agenda vazia", async () => {
  mocks.get.mockRejectedValue(new Error("Offline"));
  mount(<KitchenDayOverview recipeOpen={false} />);
  await waitFor(() => expect(screen.getAllByRole("alert")).toHaveLength(3), { timeout: 3000 });
  expect(screen.queryByText("Nenhuma atividade agendada para hoje.")).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Programação de produção" })).toHaveAttribute("href", "/producao");
});

it("respeita bloqueio dos comandos sem impedir a consulta da programação", async () => {
  mocks.get.mockResolvedValue({ data: [base] });
  mount(<KitchenProductionQueue search="" recipeOpen={false} disabled onOpen={vi.fn()} />);
  const card = await screen.findByRole("article");
  expect(within(card).getByRole("button", { name: "Iniciar OP #1" })).toBeDisabled();
  expect(within(card).getByRole("link", { name: "Detalhes da OP #1" })).toHaveAttribute("href", "/producao/op-1");
});
