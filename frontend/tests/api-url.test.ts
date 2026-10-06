import { afterEach, describe, expect, it, vi } from "vitest";
import { baseApiUrl } from "@/lib/api";

afterEach(() => vi.unstubAllEnvs());

describe("URL da API", () => {
  it("usa o mesmo domínio em produção", () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "");
    vi.stubEnv("NODE_ENV", "production");
    expect(baseApiUrl()).toBe("");
  });

  it("preserva configuração explícita e remove barra final", () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "https://api.example.com/");
    expect(baseApiUrl()).toBe("https://api.example.com");
  });

  it("usa a porta local em desenvolvimento", () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "");
    vi.stubEnv("NODE_ENV", "development");
    expect(baseApiUrl()).toBe(`${window.location.protocol}//${window.location.hostname}:8000`);
  });
});
