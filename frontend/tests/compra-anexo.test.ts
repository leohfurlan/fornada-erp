import { afterEach, expect, it, vi } from "vitest";
import { prepararAnexoCompra } from "@/lib/compra-anexo";
import { fieldIssues } from "@/lib/validation";

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it("normaliza o MIME alternativo da câmera sem perder os bytes", async () => {
  const original = new File(["foto"], "camera.jpg", { type: "image/jpg" });
  const result = await prepararAnexoCompra(original);
  expect(result.type).toBe("image/jpeg");
  expect(result.size).toBe(original.size);
});

it("reduz foto maior que 8 MB e libera o bitmap da câmera", async () => {
  const close = vi.fn();
  const decode = vi.fn().mockResolvedValue({ width: 6000, height: 8000, close });
  vi.stubGlobal("createImageBitmap", decode);
  const draw = vi.fn();
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({ fillRect: vi.fn(), drawImage: draw } as unknown as CanvasRenderingContext2D);
  vi.spyOn(HTMLCanvasElement.prototype, "toBlob").mockImplementation(callback => callback(new Blob(["jpeg"], { type: "image/jpeg" })));
  const original = new File([new Uint8Array(8 * 1024 * 1024 + 1)], "camera.jpg", { type: "image/jpeg" });
  const result = await prepararAnexoCompra(original);
  expect(result.size).toBeLessThanOrEqual(8 * 1024 * 1024);
  expect(result.type).toBe("image/jpeg");
  expect(decode).toHaveBeenCalledWith(original, { imageOrientation: "from-image" });
  expect(draw.mock.calls[0][3]).toBeLessThanOrEqual(4096);
  expect(draw.mock.calls[0][4]).toBeLessThanOrEqual(4096);
  expect(close).toHaveBeenCalledOnce();
});

it("identifica o campo do arquivo quando a foto não pode ser aberta", async () => {
  vi.stubGlobal("createImageBitmap", vi.fn().mockRejectedValue(new Error("decode")));
  try {
    await prepararAnexoCompra(new File([new Uint8Array(8 * 1024 * 1024 + 1)], "camera.jpg", { type: "image/jpeg" }));
    throw new Error("Expected failure");
  } catch (error) {
    expect(fieldIssues(error)[0].path).toBe("arquivo");
    expect(fieldIssues(error)[0].message).toContain("galeria");
  }
});

it("não tenta converter PDF grande em imagem no navegador", async () => {
  const decode = vi.fn(); vi.stubGlobal("createImageBitmap", decode);
  await expect(prepararAnexoCompra(new File([new Uint8Array(8 * 1024 * 1024 + 1)], "cupom.pdf", { type: "application/pdf" }))).rejects.toThrow("PDF ultrapassa 8 MB");
  expect(decode).not.toHaveBeenCalled();
});
