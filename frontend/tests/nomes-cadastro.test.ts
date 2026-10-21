import { describe, expect, it } from "vitest";
import { erroNome, nomeMaiusculo } from "@/lib/nomes";

describe("nomes dos cadastros", () => {
  it.each(["Bolo 🍰", "Creme ❤️", "Chef 👩‍🍳", "Bolo 🇧🇷", "Bolo 1️⃣", "a\u200bb", "a\nb", "", "a".repeat(201)])("rejeita %s", (nome) => {
    expect(erroNome(nome)).not.toBeNull();
  });
  it("mantém acentos e símbolos operacionais", () => {
    expect(nomeMaiusculo("seduc\u0327a\u0303o")).toBe("SEDUÇÃO");
    expect(erroNome("ÁGUA 20°C / 50%")).toBeNull();
  });
});
