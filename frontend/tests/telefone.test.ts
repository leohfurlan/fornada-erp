import { describe, expect, it } from "vitest";
import { mascararWhatsApp } from "@/lib/telefone";
describe("telefone", () => {
  it("preserva nono dígito ao aplicar máscara brasileira", () => {
    expect(mascararWhatsApp("11987654321", "BR")).toBe("(11) 98765-4321");
  });
  it("permite formato nacional de outro país", () => {
    expect(mascararWhatsApp("912 345 678", "PT")).toBe("912345678");
  });
});
