import { AxiosError } from "axios";
import { expect, it } from "vitest";
import { api } from "@/lib/api";
import { fieldIssues } from "@/lib/validation";

it("normaliza a resposta real do Axios e mantém o caminho para destacar o campo", async () => {
  const adapter = api.defaults.adapter;
  api.defaults.adapter = async config => {
    throw new AxiosError("validation", "ERR_BAD_REQUEST", config, undefined, {
      config, status: 422, statusText: "Unprocessable Content", headers: {}, data: {
        detail: [{ loc: ["body", "itens", 2, "produto_novo", "marca"], type: "string_too_short", msg: "String should have at least 1 character", ctx: { min_length: 1 }, input: "" }],
      },
    });
  };
  try {
    await api.post("/compras/v2/prever", {});
    throw new Error("Expected validation failure");
  } catch (error) {
    expect(error).toBeInstanceOf(AxiosError);
    const data = (error as AxiosError<{ detail: string }>).response?.data;
    expect(data?.detail).toContain("Item 3 — Marca:");
    expect(data?.detail).not.toContain("String should");
    expect(fieldIssues(error)).toEqual([{ path: "itens.2.produto_novo.marca", message: "Informe pelo menos 1 caractere(s)." }]);
  } finally { api.defaults.adapter = adapter; }
});
