import { fireEvent, render, screen, waitFor, cleanup } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ValidationScope, ValidatedForm } from "@/components/shared/validation-feedback";
import { erroCompras } from "@/lib/compras";
import { Controller, useForm } from "@/lib/form";
import { DecimalInput } from "@/components/shared/decimal-input";
afterEach(cleanup);

const error = { isAxiosError: true, response: { data: { detail: [{ loc: ["body", "itens", 1, "produto_novo", "marca"], type: "string_too_short", msg: "String should have at least 1 character", ctx: { min_length: 1 } }] } } };
it("preserva campo e índice ao apresentar o erro da API em português", () => {
  expect(erroCompras(error)).toContain("Item 2 — Marca");
  expect(erroCompras(error)).not.toContain("String should");
});
it("marca somente o campo exato, associa a mensagem e abre a seção", async () => {
  render(<ValidationScope error={error}><input aria-label="Marca 1" name="itens.0.produto_novo.marca" /><details><summary>Produto</summary><label htmlFor="marca2">Marca</label><input id="marca2" name="itens.1.produto_novo.marca" aria-describedby="hint" /><p id="hint">Ajuda</p></details></ValidationScope>);
  const field = screen.getByLabelText("Marca", { selector: "input" });
  await waitFor(() => expect(field).toHaveAttribute("aria-invalid", "true"));
  expect(screen.getByLabelText("Marca 1")).not.toHaveAttribute("aria-invalid");
  expect(field.closest("details")).toHaveAttribute("open");
  expect(field).toHaveFocus();
  expect(field).toHaveAccessibleDescription(/Ajuda Item 2 — Marca/);
  fireEvent.change(field, { target: { value: "Marca preenchida" } });
  await waitFor(() => expect(field).not.toHaveAttribute("aria-invalid"));
  expect(field).toHaveAttribute("aria-describedby", "hint");
});
it("liga validação local de Controller ao controle decimal e ao resumo", async () => {
  function Form() {
    const { control, handleSubmit, formState: { errors } } = useForm<{ quantidade: number }>({ defaultValues: { quantidade: 0 } });
    return <ValidatedForm errors={errors} onSubmit={handleSubmit(() => {})}><label>Quantidade</label><Controller name="quantidade" control={control} rules={{ validate: value => value > 0 || "Informe um valor maior que zero." }} render={({ field }) => <DecimalInput value={field.value} onChange={field.onChange} />} /><button>Salvar</button></ValidatedForm>;
  }
  render(<Form />); fireEvent.click(screen.getByText("Salvar"));
  await waitFor(() => expect(screen.getByRole("textbox")).toHaveAttribute("aria-invalid", "true"));
  expect(screen.getByRole("alert")).toHaveTextContent("Quantidade: Informe um valor maior que zero.");
});
it("falhas operacionais não tornam campos arbitrários inválidos", () => {
  render(<ValidationScope error={{ response: { data: { detail: "Serviço indisponível. Tente novamente." } } }}><input aria-label="Nome" /></ValidationScope>);
  expect(screen.getByLabelText("Nome")).not.toHaveAttribute("aria-invalid");
  expect(screen.getByRole("alert")).toHaveTextContent("Serviço indisponível");
});

it("permite reenviar depois de um erro de servidor e marca novamente se a resposta repetir", async () => {
  const submit = vi.fn().mockRejectedValue({ response: { data: { field_errors: [{ path: "marca", message: "Informe a marca." }] } } });
  function Form() {
    const { register, handleSubmit, formState: { errors } } = useForm<{ marca: string }>({ defaultValues: { marca: "" } });
    return <ValidatedForm errors={errors} onSubmit={handleSubmit(submit)}><input aria-label="Marca" {...register("marca")} /><button>Enviar</button></ValidatedForm>;
  }
  render(<Form />);
  fireEvent.click(screen.getByText("Enviar"));
  await waitFor(() => expect(screen.getByLabelText("Marca")).toHaveAttribute("aria-invalid", "true"));
  fireEvent.change(screen.getByLabelText("Marca"), { target: { value: "X" } });
  fireEvent.click(screen.getByText("Enviar"));
  await waitFor(() => expect(submit).toHaveBeenCalledTimes(2));
  await waitFor(() => expect(screen.getByLabelText("Marca")).toHaveAttribute("aria-invalid", "true"));
});

it("trata validação nativa com nome e destaque do campo", async () => {
  render(<ValidatedForm><label htmlFor="email">E-mail</label><input id="email" name="email" required type="email" /><button>Enviar</button></ValidatedForm>);
  fireEvent.click(screen.getByText("Enviar"));
  await waitFor(() => expect(screen.getByLabelText("E-mail")).toHaveAttribute("aria-invalid", "true"));
  expect(screen.getByRole("alert")).toHaveTextContent("E-mail: Preencha este campo.");
});
