import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, render } from "@testing-library/react";
import Layout from "@/app/(dashboard)/layout";

const state = vi.hoisted(() => ({ authenticated: false, hydrated: false, finish: () => {}, push: vi.fn() }));
vi.mock("next/navigation", () => ({ usePathname: () => "/receitas/abc", useRouter: () => ({ push: state.push }) }));
vi.mock("@/hooks/use-dashboard", () => ({ useDashboardResumo: () => ({ data: undefined }) }));
vi.mock("@/stores/use-auth-store", () => ({ useAuthStore: Object.assign(() => ({ isAuthenticated: state.authenticated, usuario: null, logout: vi.fn() }), { persist: {
  hasHydrated: () => state.hydrated,
  onFinishHydration: (callback: () => void) => { state.finish = callback; return vi.fn(); },
} }) }));
beforeEach(() => { cleanup(); state.authenticated = false; state.hydrated = false; state.push.mockClear(); });
describe("sessão persistida", () => {
  it("aguarda sessão salva antes de decidir redirecionamento", () => {
    render(<Layout><p>Ficha</p></Layout>);
    expect(state.push).not.toHaveBeenCalled();
    act(() => { state.authenticated = true; state.finish(); });
    expect(state.push).not.toHaveBeenCalled();
  });
  it("redireciona se não há sessão depois de carregar o armazenamento", () => {
    render(<Layout><p>Ficha</p></Layout>);
    act(() => state.finish());
    expect(state.push).toHaveBeenCalledWith("/login");
  });
});
