import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { useAuthStore } from "@/stores/use-auth-store";
import { useRascunho } from "@/hooks/use-rascunho";
import { RascunhoFeedback } from "@/components/shared/rascunho-feedback";
import { FormReceita } from "@/components/shared/form-receita";

vi.mock("@/hooks/use-estoque", () => ({ useIngredientes: () => ({ data: [] }) }));
vi.mock("@/hooks/use-configuracoes", () => ({ useEtapasPadrao: () => ({ data: [] }) }));

const exit = vi.fn();
const key = "fornada:rascunho:v1:tenant-1:user-1:teste";
function Editor({ id = "teste" }: { id?: string }) {
  const [value, setValue] = useState({ texto: "", revisao: 1 });
  const draft = useRascunho(id, { texto: "", revisao: 1 }, setValue);
  return <>
    <input aria-label="Texto" value={value.texto} onChange={e => {
      const next = { ...value, texto: e.target.value };
      draft.persist(next); setValue(next);
    }} />
    <a href="/outra" onClick={e => { e.preventDefault(); exit(); }}>Voltar</a>
    <button data-rascunho-sair onClick={exit}>Sair</button>
    <button onClick={() => draft.complete(value)}>Salvar definitivo</button>
    <RascunhoFeedback {...draft} />
  </>;
}

beforeEach(() => {
  localStorage.clear(); exit.mockReset();
  useAuthStore.setState({ usuario: { id: "user-1", tenant_id: "tenant-1", nome: "Teste", email: "teste@example.com", valor_hora: "0" } });
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("rascunhos locais", () => {
  it("recupera a última digitação após fechar e reabrir, sem depender do evento de fechamento", () => {
    const view = render(<Editor />);
    fireEvent.change(screen.getByLabelText("Texto"), { target: { value: "Minha receita incompleta" } });
    expect(JSON.parse(localStorage.getItem(key)!).value.texto).toBe("Minha receita incompleta");
    view.unmount(); render(<Editor />);
    expect(screen.getByLabelText("Texto")).toHaveValue("Minha receita incompleta");
    expect(screen.getByText(/Rascunho recuperado/)).toBeInTheDocument();
  });
  it("confirma navegação e permite continuar, salvar ou descartar", () => {
    render(<Editor />);
    fireEvent.change(screen.getByLabelText("Texto"), { target: { value: "Bolo" } });
    fireEvent.click(screen.getByText("Voltar"));
    expect(exit).not.toHaveBeenCalled();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Continuar editando"));
    expect(screen.getByLabelText("Texto")).toHaveValue("Bolo");
    fireEvent.click(screen.getByText("Voltar"));
    fireEvent.click(screen.getByText("Salvar rascunho e sair"));
    expect(exit).toHaveBeenCalledOnce();
    expect(localStorage.getItem(key)).not.toBeNull();
  });
  it("intercepta logout antes de executar e apaga somente quando descarta", () => {
    render(<Editor />);
    fireEvent.change(screen.getByLabelText("Texto"), { target: { value: "Bolo" } });
    fireEvent.click(screen.getByText("Sair"));
    expect(exit).not.toHaveBeenCalled();
    fireEvent.click(screen.getByText("Descartar e sair"));
    expect(exit).toHaveBeenCalledOnce();
    expect(localStorage.getItem(key)).toBeNull();
  });
  it("protege voltar do dispositivo e recarregar, mas não bloqueia após salvar", () => {
    render(<Editor />);
    fireEvent.change(screen.getByLabelText("Texto"), { target: { value: "Bolo" } });
    fireEvent(window, new PopStateEvent("popstate"));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Continuar editando"));
    const before = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(before);
    expect(before.defaultPrevented).toBe(true);
    fireEvent.click(screen.getByText("Salvar definitivo"));
    expect(localStorage.getItem(key)).toBeNull();
    const after = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(after);
    expect(after.defaultPrevented).toBe(false);
  });
  it("separa conta, receita e ficha técnica", () => {
    localStorage.setItem(key, JSON.stringify({ value: { texto: "Privado", revisao: 1 } }));
    const view = render(<Editor id="ficha:outra" />);
    expect(screen.getByLabelText("Texto")).toHaveValue("");
    view.unmount();
    useAuthStore.setState({ usuario: { ...useAuthStore.getState().usuario!, tenant_id: "outro-tenant" } });
    render(<Editor />);
    expect(screen.getByLabelText("Texto")).toHaveValue("");
  });
  it("avisa se o armazenamento falhar e impede sair com falsa confirmação de salvamento", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("quota"); });
    render(<Editor />);
    fireEvent.change(screen.getByLabelText("Texto"), { target: { value: "Bolo" } });
    expect(screen.getByText(/Não foi possível salvar o rascunho/)).toBeInTheDocument();
    fireEvent.click(screen.getByText("Sair"));
    fireEvent.click(screen.getByText("Salvar rascunho e sair"));
    expect(exit).not.toHaveBeenCalled();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });
  it("preserva campos e listas dinâmicas do formulário real de receita após remontar", async () => {
    const props = { textoBotao: "Salvar receita", textoBotaoLoading: "Salvando", onSubmit: vi.fn() };
    const view = render(<FormReceita {...props} />);
    fireEvent.change(screen.getByPlaceholderText("Ex: Bolo de chocolate"), { target: { value: "Bolo de chocolate" } });
    fireEvent.change(screen.getByLabelText("Modo de preparo"), { target: { value: "1. Misture **bem**." } });
    fireEvent.click(screen.getByText("Adicionar ingrediente"));
    view.unmount();
    render(<FormReceita {...props} />);
    await waitFor(() => expect(screen.getByPlaceholderText("Ex: Bolo de chocolate")).toHaveValue("BOLO DE CHOCOLATE"));
    expect(screen.getByLabelText("Modo de preparo")).toHaveValue("1. Misture **bem**.");
    expect(screen.getByText("Ingrediente 2")).toBeInTheDocument();
  });

  it("mantém a receita recuperável quando a API falha e limpa após salvar definitivamente", async () => {
    const onSubmit = vi.fn().mockRejectedValueOnce(new Error("offline")).mockResolvedValue(undefined);
    render(<FormReceita textoBotao="Salvar receita" textoBotaoLoading="Salvando" onSubmit={onSubmit} valoresIniciais={{
      nome: "BOLO", categoria: "Bolos", rendimento: 1, rendimento_unidade: "un",
      ingredientes: [{ ingrediente_id: "ingrediente-1", quantidade: 2, unidade: "g" }],
      etapas: [{ nome: "Misturar", duracao_minutos: 5, tipo_mao_obra: "direta", ordem: 0 }],
    }} />);
    fireEvent.change(screen.getByLabelText("Modo de preparo"), { target: { value: "Misture bem" } });
    const form = screen.getByRole("button", { name: "Salvar receita" }).closest("form")!;
    fireEvent.submit(form);
    await waitFor(() => expect(onSubmit).toHaveBeenCalledOnce());
    await screen.findAllByText(/Não foi possível concluir a operação/);
    const recipeKey = "fornada:rascunho:v1:tenant-1:user-1:receita:nova";
    expect(localStorage.getItem(recipeKey)).toContain("Misture bem");
    fireEvent.submit(form);
    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(localStorage.getItem(recipeKey)).toBeNull());
  });
});
