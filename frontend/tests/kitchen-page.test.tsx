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
      name: "Bolo", yield_quantity: "1", yield_unit: "un", ingredients: [], warnings: [], completed_block_ids: [] as string[],
      blocks: [
        { id: "step-1", section: "steps", checkable: true, title: "Misturar", markdown: "Duração: 5 min" },
        { id: "preparation-text", section: "preparation", checkable: false, title: "Modo de preparo", markdown: "1. Texto integral para leitura\n2. Continue a receita" },
      ],
    },
  };
  mocks.get.mockImplementation(async (path: string) => {
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

it("exibe o modo de preparo como texto único sem controle de conclusão", async () => {
  const { station, client } = await openKitchen();
  station.section = "preparation";
  station.revision++;
  await act(async () => { await client.invalidateQueries({ queryKey: ["cozinha", "cook", "station"] }); });
  expect(await screen.findByText(/Texto integral para leitura/)).toBeVisible();
  expect(screen.queryByRole("button", { name: "Marcar etapa 1 como concluída" })).not.toBeInTheDocument();
  fireEvent.click(screen.getByText(/Texto integral para leitura/));
  expect(mocks.post.mock.calls.filter(([path]) => path.endsWith("/commands"))).toHaveLength(0);
  expect(screen.getByText("0 de 1 etapas concluídas")).toBeVisible();
  expect(screen.queryByRole("button", { name: "Próxima etapa" })).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Repetir leitura" })).toBeVisible();
});
