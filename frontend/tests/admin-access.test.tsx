import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import AdminPage from "@/app/(dashboard)/admin/page";

const state = vi.hoisted(() => ({ admin: true, iniciar: vi.fn(), query: vi.fn() }));
vi.mock("@/stores/use-auth-store", () => ({ useAuthStore: () => ({ usuario: {
  id: "operator", nome: "Operador", is_superuser: state.admin,
} }) }));
vi.mock("@/hooks/use-admin", () => ({
  iniciarSuporte: state.iniciar,
  useContasAdmin: (q: string, offset: number, enabled: boolean) => {
    state.query(q, offset, enabled);
    return { data: enabled ? [{ id: "target", tenant_id: "tenant", nome: "Cliente",
      email: "cliente@example.com", negocio: "Loja teste", ativo: true, is_superuser: false }] : undefined };
  },
}));

beforeEach(() => { cleanup(); state.admin = true; state.iniciar.mockReset(); state.query.mockClear(); });

describe("acesso administrativo", () => {
  it("não solicita o diretório nem mostra contas para um usuário normal", () => {
    state.admin = false;
    render(<AdminPage />);
    expect(state.query).toHaveBeenCalledWith("", 0, false);
    expect(screen.getByText("Acesso exclusivo da administração.")).toBeInTheDocument();
    expect(screen.queryByText("cliente@example.com")).not.toBeInTheDocument();
  });

  it("exige motivo e confirmação identificando a conta antes do suporte", () => {
    render(<AdminPage />);
    fireEvent.click(screen.getByRole("button", { name: "Acessar conta" }));
    expect(screen.getByRole("dialog", { name: "Acessar Loja teste" })).toBeInTheDocument();
    expect(screen.getByLabelText("Motivo do suporte")).toHaveFocus();
    expect(screen.getByText(/Você poderá consultar e alterar dados desta conta durante 15 minutos/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirmar acesso" })).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Motivo do suporte"), { target: { value: "   " } });
    expect(screen.getByRole("button", { name: "Confirmar acesso" })).toBeDisabled();
    expect(state.iniciar).not.toHaveBeenCalled();
  });

  it("fecha pelo botão Cancelar e devolve o foco ao acesso da conta", async () => {
    render(<AdminPage />);
    const acesso = screen.getByRole("button", { name: "Acessar conta" });
    fireEvent.click(acesso);
    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await waitFor(() => expect(acesso).toHaveFocus());
    expect(state.iniciar).not.toHaveBeenCalled();
  });

  it("fecha o modal com Escape sem abrir uma sessão de suporte", () => {
    render(<AdminPage />);
    fireEvent.click(screen.getByRole("button", { name: "Acessar conta" }));
    fireEvent.keyDown(screen.getByLabelText("Motivo do suporte"), { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(state.iniciar).not.toHaveBeenCalled();
  });

  it("mantém o motivo e permite tentar novamente quando a abertura falha", async () => {
    state.iniciar.mockRejectedValue(new Error("indisponível"));
    render(<AdminPage />);
    fireEvent.click(screen.getByRole("button", { name: "Acessar conta" }));
    fireEvent.change(screen.getByLabelText("Motivo do suporte"), { target: { value: "Revisar pedido" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirmar acesso" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Não foi possível abrir a conta."));
    expect(state.iniciar).toHaveBeenCalledWith("target", "Revisar pedido");
    expect(screen.getByLabelText("Motivo do suporte")).toHaveValue("Revisar pedido");
    expect(screen.getByRole("button", { name: "Confirmar acesso" })).toBeEnabled();
  });
});
