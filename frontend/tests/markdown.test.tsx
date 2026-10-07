import { useState } from "react";
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MarkdownContent } from "@/components/shared/markdown-content";
import { MarkdownField } from "@/components/shared/markdown-field";

afterEach(cleanup);

function Editor({ initial = "", required = false, maxLength }: { initial?: string; required?: boolean; maxLength?: number }) {
  const [value, setValue] = useState(initial);
  return <MarkdownField label="Modo de preparo" value={value} onChange={setValue} required={required} maxLength={maxLength} />;
}

describe("Markdown", () => {
  it("formata títulos, ênfase, listas, tabelas e links", () => {
    render(<MarkdownContent>{"## Preparo\n\nMisture **chocolate** e *leite*.\n\n1. Bater\n2. Assar\n\n> Deixe esfriar.\n\n| Etapa | Tempo |\n| --- | --- |\n| Forno | 30 min |\n\n[Referência](https://example.com)"}</MarkdownContent>);
    expect(screen.getByRole("heading", { name: "Preparo", level: 2 })).toBeInTheDocument();
    expect(screen.getByText("chocolate").tagName).toBe("STRONG");
    expect(screen.getByText("leite").tagName).toBe("EM");
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Referência" })).toHaveAttribute("href", "https://example.com");
  });

  it("não executa HTML nem permite links javascript ou imagens data", () => {
    const { container } = render(<MarkdownContent>{'<script>alert("teste")</script>\n\n<img src="x" onerror="alert(1)">\n\n[perigoso](javascript:alert%281%29)\n\n![imagem](data:text/html;base64,dGVzdGU=)'}</MarkdownContent>);
    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector("[onerror]")).toBeNull();
    expect(screen.getByText("perigoso").closest("a")).toBeNull();
    expect(container.querySelector("img")).toBeNull();
  });

  it("preserva texto simples e quebras de linha de conteúdos antigos", () => {
    const { container } = render(<MarkdownContent>{"Misture os ingredientes.\nAsse a 180°C."}</MarkdownContent>);
    expect(container.querySelector("p")?.textContent).toBe("Misture os ingredientes.\nAsse a 180°C.");
    expect(container.querySelector("p")).toHaveClass("whitespace-pre-line");
  });

  it("a prévia não altera o texto Markdown do editor", () => {
    const source = "## Forno\n\n**Assar** por 30 minutos.";
    render(<Editor initial={source} />);
    fireEvent.click(screen.getByRole("button", { name: "Modo de preparo: prévia" }));
    expect(screen.getByRole("heading", { name: "Forno" })).toBeInTheDocument();
    expect(screen.getByText("Assar").tagName).toBe("STRONG");
    fireEvent.click(screen.getByRole("button", { name: "Modo de preparo: editar" }));
    expect(screen.getByLabelText("Modo de preparo")).toHaveValue(source);
  });

  it("formata a seleção, mantém o cursor e respeita o limite do campo", async () => {
    render(<Editor initial="Chocolate" maxLength={20} />);
    const field = screen.getByLabelText<HTMLTextAreaElement>("Modo de preparo");
    field.setSelectionRange(0, 9);
    fireEvent.click(screen.getByRole("button", { name: "Modo de preparo: negrito" }));
    expect(field).toHaveValue("**Chocolate**");
    await waitFor(() => expect(field).toHaveFocus());
    expect(field.selectionStart).toBe(2);
    expect(field.selectionEnd).toBe(11);
    fireEvent.click(screen.getByRole("button", { name: "Modo de preparo: link" }));
    expect(field).toHaveValue("**Chocolate**");
  });

  it("retorna à edição quando um campo obrigatório vazio é inválido na prévia", () => {
    render(<Editor required />);
    fireEvent.click(screen.getByRole("button", { name: "Modo de preparo: prévia" }));
    expect(screen.getByText("Nenhum texto para visualizar.")).toBeInTheDocument();
    fireEvent.invalid(screen.getByLabelText("Modo de preparo"));
    expect(screen.queryByRole("region", { name: "Prévia de Modo de preparo" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Modo de preparo")).not.toHaveClass("sr-only");
  });
});
