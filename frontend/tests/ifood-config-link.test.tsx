import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ConfiguracoesPage from "@/app/(dashboard)/configuracoes/page";

describe("acesso ao monitor iFood", () => {
  it("exibe o atalho do monitor na página de configurações", () => {
    render(<ConfiguracoesPage />);

    expect(screen.getByRole("link", { name: /Monitor iFood/ })).toHaveAttribute(
      "href",
      "/configuracoes/integracoes/ifood",
    );
  });
});
