import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";
import { PwaProvider } from "@/components/shared/pwa-provider";
import { PwaInstall, PwaInstallMenu } from "@/components/shared/pwa-install";
import { ADIAMENTO_MS } from "@/lib/pwa";

const state = vi.hoisted(() => ({ hydrated: true, authenticated: true, user: { id: "user", tenant_id: "tenant" }, finish: () => {}, support: false, standalone: false, post: vi.fn() }));
vi.mock("@/stores/use-auth-store", () => {
  const get = () => ({ usuario: state.user, isAuthenticated: state.authenticated });
  return { useAuthStore: Object.assign(get, { getState: get, persist: {
    hasHydrated: () => state.hydrated, onFinishHydration: (cb: () => void) => { state.finish = cb; return () => {}; },
  } }) };
});
vi.mock("@/lib/admin-session", () => ({ getSupportSession: () => state.support ? {} : null }));
vi.mock("@/lib/api", () => ({ api: { post: state.post } }));
function app() { return <PwaProvider><PwaInstall /><PwaInstallMenu /></PwaProvider>; }
function offer(outcome: "accepted" | "dismissed" = "accepted") {
  const prompt = vi.fn().mockResolvedValue({ outcome });
  const event = Object.assign(new Event("beforeinstallprompt", { cancelable: true }), { prompt, userChoice: Promise.resolve({ outcome }) });
  act(() => { window.dispatchEvent(event); }); return prompt;
}
beforeEach(() => {
  state.hydrated = true; state.authenticated = true; state.support = false; state.standalone = false;
  state.user = { id: "user", tenant_id: "tenant" }; localStorage.clear();
  state.post.mockReset().mockResolvedValue({});
  vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: state.standalone, addEventListener: vi.fn(), removeEventListener: vi.fn() })));
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
describe("convite de instalação", () => {
  it("aguarda hidratação e usa evento capturado antes dela", async () => {
    state.hydrated = false; render(app()); offer();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    act(() => { state.hydrated = true; state.finish(); });
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
  });
  it("aciona prompt uma vez e distingue escolha, instalação e uso", async () => {
    render(app()); const prompt = offer();
    fireEvent.click(await screen.findByRole("button", { name: "Instalar" }));
    expect(prompt).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(state.post).toHaveBeenCalledWith("/pwa/eventos", expect.objectContaining({ tipo: "confirmacao_aceita" }), expect.any(Object)));
    expect(state.post.mock.calls.some(([, payload]) => payload.tipo === "acesso_app")).toBe(false);
    act(() => { window.dispatchEvent(new Event("appinstalled")); });
    expect(state.post).toHaveBeenCalledWith("/pwa/eventos", expect.objectContaining({ tipo: "instalacao_sinalizada" }), expect.any(Object));
  });
  it("adia sete dias e mantém opção manual", async () => {
    render(app()); offer(); fireEvent.click(await screen.findByText("Agora não"));
    expect(Number(localStorage.getItem("fornada-pwa-adiar:tenant:user"))).toBeGreaterThan(Date.now() + ADIAMENTO_MS - 1000);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByText("Instalar aplicativo")).toBeInTheDocument();
    cleanup(); render(app()); offer(); expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
  it.each([ADIAMENTO_MS - 1, ADIAMENTO_MS])("respeita limite exato do adiamento %s", async (elapsed) => {
    const now = Date.now(); vi.spyOn(Date, "now").mockReturnValue(now);
    localStorage.setItem("fornada-pwa-adiar:tenant:user", String(now + ADIAMENTO_MS - elapsed));
    render(app()); offer();
    expect(Boolean(screen.queryByRole("dialog"))).toBe(elapsed === ADIAMENTO_MS);
    vi.restoreAllMocks();
  });
  it("não oferece em modo aplicativo e registra acesso uma vez", () => {
    state.standalone = true; render(app()); offer();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(state.post.mock.calls.filter(([, payload]) => payload.tipo === "acesso_app")).toHaveLength(1);
  });
  it("não oferece nem registra durante suporte", () => {
    state.support = true; render(app()); offer();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument(); expect(state.post).not.toHaveBeenCalled();
  });
  it("sem evento não mostra convite ou botão", () => {
    render(app()); expect(screen.queryByRole("dialog")).not.toBeInTheDocument(); expect(screen.queryByText("Instalar aplicativo")).not.toBeInTheDocument();
  });
  it("registra recusa sem inferir instalação", async () => {
    render(app()); offer("dismissed");
    fireEvent.click(await screen.findByRole("button", { name: "Instalar" }));
    await waitFor(() => expect(state.post.mock.calls.some(([, payload]) => payload.tipo === "confirmacao_recusada")).toBe(true));
    expect(state.post.mock.calls.some(([, payload]) => payload.tipo === "instalacao_sinalizada")).toBe(false);
  });
  it("falha de telemetria repete com a mesma chave e não impede a instalação", async () => {
    state.post.mockRejectedValue(new Error("offline"));
    render(app()); const prompt = offer();
    fireEvent.click(await screen.findByRole("button", { name: "Instalar" }));
    expect(prompt).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(state.post.mock.calls.filter(([, payload]) => payload.tipo === "confirmacao_aceita")).toHaveLength(2));
    const attempts = state.post.mock.calls.filter(([, payload]) => payload.tipo === "confirmacao_aceita");
    expect(attempts[0][1].event_id).toBe(attempts[1][1].event_id);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
  it("storage indisponível mantém adiamento em memória sem reabrir na sessão", async () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => { throw new Error("blocked"); });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("blocked"); });
    render(app()); offer(); fireEvent.click(await screen.findByText("Agora não"));
    offer(); expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    vi.restoreAllMocks();
  });
  it("Escape adia e não chama o prompt nativo", async () => {
    render(app()); const prompt = offer();
    fireEvent.keyDown(await screen.findByRole("dialog"), { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(prompt).not.toHaveBeenCalled(); expect(localStorage.getItem("fornada-pwa-adiar:tenant:user")).not.toBeNull();
  });
  it("troca de conta descarta evento e callbacks antigos", async () => {
    const view = render(app()); offer();
    state.user = { id: "other", tenant_id: "other-tenant" }; view.rerender(app());
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument(); expect(screen.queryByText("Instalar aplicativo")).not.toBeInTheDocument();
  });
  it("erro de prompt mantém aplicação e informa falha sem sucesso inventado", async () => {
    render(app()); const prompt = offer(); prompt.mockRejectedValueOnce(new Error("blocked"));
    fireEvent.click(await screen.findByRole("button", { name: "Instalar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível abrir");
    expect(state.post.mock.calls.some(([, payload]) => payload.tipo === "confirmacao_aceita")).toBe(false);
  });
});
