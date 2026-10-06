import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { WhatsAppAccess } from "@/components/shared/whatsapp-access";

const mocks = vi.hoisted(() => ({ solicitar: vi.fn(), verificar: vi.fn(), entrar: vi.fn(), vincular: vi.fn(), push: vi.fn(), setUsuario: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: mocks.push }) }));
vi.mock("@/stores/use-auth-store", () => ({ useAuthStore: () => ({ setUsuario: mocks.setUsuario, setTokens: vi.fn() }) }));
vi.mock("@/hooks/use-whatsapp-auth", () => ({
  useWhatsAppDisponivel: () => ({ data: { ativo: true } }),
  useSolicitarWhatsApp: () => ({ mutateAsync: mocks.solicitar }),
  useVerificarWhatsApp: () => ({ mutateAsync: mocks.verificar }),
  useEntrarWhatsApp: () => ({ mutateAsync: mocks.entrar }),
  useCadastrarWhatsApp: () => ({ mutateAsync: vi.fn() }),
  useVincularWhatsApp: () => ({ mutateAsync: mocks.vincular }),
}));
beforeEach(() => { cleanup(); vi.clearAllMocks(); mocks.solicitar.mockResolvedValue({ desafio: "desafio", reenviar_em: 60 }); mocks.verificar.mockResolvedValue({ prova: "validada" }); });
describe("acesso WhatsApp", () => {
  it("pede dados cadastrais somente depois da validação do código", async () => {
    mocks.entrar.mockResolvedValue({ tokens: null, onboarding_prova: "onboarding" });
    render(<WhatsAppAccess />);
    expect(screen.queryByLabelText("Seu nome")).toBeNull();
    fireEvent.change(screen.getByLabelText("Número do WhatsApp"), { target: { value: "11987654321" } });
    fireEvent.click(screen.getByRole("button", { name: "Receber código" }));
    await screen.findByLabelText("Código de acesso");
    expect(mocks.solicitar).toHaveBeenCalledWith({ telefone: "(11) 98765-4321", regiao: "BR" });
    expect(screen.getByRole("button", { name: /Reenviar em/ })).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Código de acesso"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Validar código" }));
    await screen.findByLabelText("Seu nome");
    expect(mocks.verificar).toHaveBeenCalledWith({ desafio: "desafio", codigo: "123456" });
    expect(screen.getByLabelText("Cidade")).toBeTruthy();
  });
  it("vincula número somente à conta atual, sem iniciar outra sessão", async () => {
    mocks.vincular.mockResolvedValue({ nome: "Usuária" });
    render(<WhatsAppAccess vincular />);
    fireEvent.change(screen.getByLabelText("Número do WhatsApp"), { target: { value: "11987654321" } });
    fireEvent.click(screen.getByRole("button", { name: "Receber código" }));
    await screen.findByLabelText("Código de acesso");
    fireEvent.change(screen.getByLabelText("Código de acesso"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Validar código" }));
    await waitFor(() => expect(mocks.vincular).toHaveBeenCalledWith({ prova: "validada" }));
    expect(mocks.entrar).not.toHaveBeenCalled();
    await screen.findByText("WhatsApp vinculado à sua conta.");
  });
});
