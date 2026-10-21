import { afterEach, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import CozinhaPage from "@/app/(dashboard)/cozinha/page";

const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("@/lib/api", () => ({ api: mocks }));
vi.mock("@/stores/use-auth-store", () => ({
  useAuthStore: (selector: (state: { usuario: { id: string }; isAuthenticated: boolean }) => unknown) => selector({ usuario: { id: "cook" }, isAuthenticated: true }),
}));
afterEach(() => { cleanup(); vi.resetAllMocks(); });

async function openKitchen() {
  const station = {
    id: "station", name: "Bancada", status: "active", revision: 1,
    recipe_id: "recipe", section: "steps", block_index: 0, speech_part_index: 0,
    rendered_revision: 1, notice: null,
    projection: {
      recipe_id: "recipe", recipe_version: "v1", session_id: "session",
      name: "Bolo", yield_quantity: "1", yield_unit: "un", ingredients: [{ id: "ingredient-0", name: "Farinha", quantity: "0.5", unit: "kg" }], warnings: [], completed_block_ids: [] as string[], checked_ingredient_ids: [] as string[],
      blocks: [
        { id: "ingredients-1", section: "ingredients", checkable: false, title: "Ingredientes", markdown: "Farinha" },
        { id: "assembly-1", section: "assembly", checkable: false, title: "Montagem", markdown: "Sirva." },
        { id: "step-1", section: "steps", checkable: true, title: "Misturar", markdown: "Duração: 5 min" },
        { id: "preparation-text", section: "preparation", checkable: false, title: "Modo de preparo", markdown: "1. Texto integral para leitura\n2. Continue a receita" },
      ],
    },
  };
  mocks.get.mockImplementation(async (path: string) => {
    if (["/agenda", "/vendas", "/producao/ordens"].includes(path)) return { data: [] };
    if (path === "/integracoes/ifood/monitor") return { data: { habilitado: false, pedidos: [] } };
    if (path.endsWith("/stations")) return { data: { items: [{ id: "station", revision: station.revision }] } };
    if (path.endsWith("/alexa/link")) return { data: { linked: false } };
    return { data: { changed: true, station: structuredClone(station) } };
  });
  mocks.post.mockImplementation(async (path: string) => {
    if (path.endsWith("/lease")) return { data: { lease_id: "lease", station: structuredClone(station) } };
    return { data: {} };
  });
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const view = render(<QueryClientProvider client={client}><CozinhaPage /></QueryClientProvider>);
  fireEvent.click(await screen.findByRole("button", { name: "Ativar modo cozinha" }));
  await screen.findByRole("button", { name: "Marcar etapa 1 como concluída" });
  return { station, client, view };
}

it("marca imediatamente, bloqueia eventos duplicados e recupera do servidor ao remontar", async () => {
  const { station, view } = await openKitchen();
  let finish!: () => void;
  mocks.post.mockImplementation((path: string) => {
    if (path.endsWith("/commands")) return new Promise(resolve => {
      finish = () => {
        station.projection.completed_block_ids = ["step-1"];
        station.revision++;
        resolve({ data: { revision: station.revision, status: "accepted" } });
      };
    });
    return Promise.resolve({ data: { lease_id: "lease", station: structuredClone(station), rendered_revision: station.revision } });
  });
  fireEvent.click(screen.getByRole("button", { name: "Marcar etapa 1 como concluída" }));
  fireEvent.click(screen.getByRole("article", { name: "Etapa 1" }));
  expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "100");
  expect(mocks.post.mock.calls.filter(([path]) => path.endsWith("/commands"))).toHaveLength(1);
  await act(async () => finish());
  await waitFor(() => expect(screen.getByRole("button", { name: "Desmarcar etapa 1" })).toBeEnabled());
  view.unmount();
  // A fresh QueryClient simulates leaving the page and reloading the application.
  render(<QueryClientProvider client={new QueryClient()}><CozinhaPage /></QueryClientProvider>);
  fireEvent.click(await screen.findByRole("button", { name: "Ativar modo cozinha" }));
  expect(await screen.findByRole("button", { name: "Desmarcar etapa 1" })).toBeVisible();
  expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "100");
});

it("desfaz a marcação otimista quando o servidor recusa o comando", async () => {
  await openKitchen();
  mocks.post.mockRejectedValue(new Error("Sem conexão"));
  fireEvent.click(screen.getByRole("button", { name: "Marcar etapa 1 como concluída" }));
  expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "100");
  await screen.findByText("Não foi possível concluir. Verifique a conexão e tente novamente.");
  await waitFor(() => expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "0"));
});

it("une texto e etapas no modo de preparo, mantendo o texto fora da seleção", async () => {
  const { station, client } = await openKitchen();
  station.section = "preparation";
  station.revision++;
  await act(async () => { await client.invalidateQueries({ queryKey: ["cozinha", "cook", "station"] }); });
  expect(await screen.findByText(/Texto integral para leitura/)).toBeVisible();
  const step = screen.getByRole("article", { name: "Etapa 1" });
  expect(screen.getByRole("button", { name: "Marcar etapa 1 como concluída" })).toBeVisible();
  expect(screen.queryByRole("button", { name: "Etapas" })).not.toBeInTheDocument();
  expect(screen.getByText(/Texto integral para leitura/).compareDocumentPosition(step) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  fireEvent.click(screen.getByText(/Texto integral para leitura/));
  expect(mocks.post.mock.calls.filter(([path]) => path.endsWith("/commands"))).toHaveLength(0);
  expect(screen.getByText("0 de 1 etapas concluídas")).toBeVisible();
  expect(screen.queryByRole("button", { name: "Próxima etapa" })).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Repetir leitura" })).toBeVisible();
});

it("mantém o texto no topo também quando a navegação está nas etapas", async () => {
  await openKitchen();
  const text = screen.getByText(/Texto integral para leitura/);
  const step = screen.getByRole("article", { name: "Etapa 1" });
  expect(text.compareDocumentPosition(step) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(screen.getByRole("button", { name: "Modo de preparo" })).toHaveClass("bg-primary");
  expect(screen.queryByRole("button", { name: "Etapas" })).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Voltar ao início do modo de preparo" })).toHaveAttribute("href", "#modo-de-preparo");
});

it("oculta a configuração após vincular conta, Echo e estação e permite gerenciar explicitamente", async () => {
  const { client } = await openKitchen();
  client.setQueryData(["cozinha", "cook", "alexa-link"], { linked: true, approved_device_id: "echo", station_id: "station", pending_devices: [] });
  await waitFor(() => expect(screen.getByText("Alexa conectada")).toBeVisible());
  expect(screen.queryByText("Como configurar a Alexa na Echo Dot 3")).not.toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "Alexa · Echo Dot" })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Gerenciar Alexa" }));
  expect(screen.getByText("Como configurar a Alexa na Echo Dot 3")).toBeInTheDocument();
});

it("apresenta as OPs antes do catálogo e abre a receita da ordem selecionada", async () => {
  const { client } = await openKitchen();
  const previousGet = mocks.get.getMockImplementation()!;
  mocks.get.mockImplementation(async (path: string, ...rest: unknown[]) => {
    if (path === "/producao/ordens") return { data: [{ id: "op", numero: 7, receita_id: "recipe", nome_receita: "Bolo", status: "planejada", qtd_planejada: "1", receita_rendimento: "10", receita_rendimento_unidade: "un", data_prevista: null, pedido_numero: null, proximas_transicoes: [] }] };
    if (path === "/cozinha/recipes/search") return { data: { items: [{ recipe_id: "other", name: "Bolo de chocolate" }], next_offset: null } };
    return previousGet(path, ...rest);
  });
  await act(async () => { await client.invalidateQueries({ queryKey: ["cozinha-operacao"] }); });
  fireEvent.change(screen.getByRole("textbox", { name: "Buscar receita" }), { target: { value: "Bolo" } });
  fireEvent.click(screen.getByRole("button", { name: "Buscar" }));
  const catalog = await screen.findByText("Bolo de chocolate");
  const order = screen.getByRole("button", { name: "Abrir receita da OP #7" });
  expect(order.compareDocumentPosition(catalog) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  fireEvent.click(order);
  await waitFor(() => expect(mocks.post).toHaveBeenCalledWith("/cozinha/stations/station/commands", expect.objectContaining({ type: "open_recipe", payload: { recipe_id: "recipe" } })));
});

it("oferece avanço entre ingredientes, preparo e montagem mesmo com um único bloco", async () => {
  const { station, client } = await openKitchen();
  expect(screen.getByRole("button", { name: "Ir para montagem" })).toBeEnabled();
  fireEvent.click(screen.getByRole("button", { name: "Ir para montagem" }));
  await waitFor(() => expect(mocks.post).toHaveBeenCalledWith(expect.stringContaining("/commands"), expect.objectContaining({ type: "show_section", payload: { section: "assembly" } })));
  station.section = "ingredients"; station.revision++;
  await act(async () => { await client.invalidateQueries({ queryKey: ["cozinha", "cook", "station"] }); });
  expect(await screen.findByRole("button", { name: "Ir para modo de preparo" })).toBeEnabled();
});

it("confere ingrediente imediatamente, envia uma vez e reverte após erro sem afetar etapas", async () => {
  const { station, client } = await openKitchen();
  station.section = "ingredients"; station.revision++;
  await act(async () => { await client.invalidateQueries({ queryKey: ["cozinha", "cook", "station"] }); });
  mocks.post.mockRejectedValue(new Error("Offline"));
  const ingredient = await screen.findByRole("button", { name: "Confirmar ingrediente Farinha à mão" });
  fireEvent.click(ingredient); fireEvent.click(ingredient);
  expect(screen.getByText("1 de 1 ingredientes à mão")).toBeVisible();
  await screen.findByText("Não foi possível concluir. Verifique a conexão e tente novamente.");
  await waitFor(() => expect(screen.getByText("0 de 1 ingredientes à mão")).toBeVisible());
  expect(mocks.post.mock.calls.filter(([path]) => path.endsWith("/commands"))).toHaveLength(1);
  expect(station.projection.completed_block_ids).toEqual([]);
});

it("fecha os resultados e foca Receita aberta ao reabrir a mesma receita", async () => {
  const { station } = await openKitchen();
  const previous = mocks.get.getMockImplementation()!;
  mocks.get.mockImplementation(async (path: string, ...rest: unknown[]) => path === "/cozinha/recipes/search" ? { data: { items: [{ recipe_id: "recipe", name: "Bolo encontrado" }], next_offset: null } } : previous(path, ...rest));
  const scroll = vi.fn();
  const header = screen.getByLabelText("Receita aberta");
  header.scrollIntoView = scroll;
  mocks.post.mockImplementation(async (path: string) => {
    if (path.endsWith("/commands")) { station.revision++; return { data: { status: "accepted", revision: station.revision } }; }
    return { data: {} };
  });
  fireEvent.change(screen.getByRole("textbox", { name: "Buscar receita" }), { target: { value: "Bolo" } });
  fireEvent.click(screen.getByRole("button", { name: "Buscar" }));
  fireEvent.click(await screen.findByRole("button", { name: "Bolo encontrado Abrir" }));
  await waitFor(() => expect(screen.queryByRole("button", { name: "Bolo encontrado Abrir" })).not.toBeInTheDocument());
  expect(screen.getByRole("textbox", { name: "Buscar receita" })).toHaveValue("");
  await waitFor(() => expect(header).toHaveFocus());
  expect(scroll).toHaveBeenCalled();
});
