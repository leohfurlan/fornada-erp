const MAX_BYTES = 8 * 1024 * 1024;

function invalidFile(message: string): Error {
  return Object.assign(new Error(message), { response: { data: {
    field_errors: [{ path: "arquivo", message }],
  } } });
}

async function mime(file: File): Promise<string> {
  const type = file.type.toLowerCase().split(";")[0];
  if (type === "image/jpg" || type === "image/pjpeg") return "image/jpeg";
  if (type && type !== "application/octet-stream") return type;
  const bytes = new Uint8Array(await file.slice(0, 12).arrayBuffer());
  if (bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) return "image/jpeg";
  if (bytes[0] === 0x89 && bytes[1] === 0x50 && bytes[2] === 0x4e && bytes[3] === 0x47) return "image/png";
  const text = String.fromCharCode(...bytes);
  if (text.startsWith("RIFF") && text.slice(8, 12) === "WEBP") return "image/webp";
  if (text.startsWith("%PDF-")) return "application/pdf";
  throw invalidFile("Não reconhecemos o formato. Escolha uma foto JPG, PNG, WebP ou um PDF.");
}

/** Normaliza o arquivo nativo; reduz fotos grandes antes de enviar ao limite da API. */
export async function prepararAnexoCompra(original: File): Promise<File> {
  if (!original.size) throw invalidFile("A foto veio vazia. Tire outra foto ou escolha uma imagem da galeria.");
  const type = await mime(original);
  if (!["image/jpeg", "image/png", "image/webp", "image/heic", "application/pdf"].includes(type)) {
    throw invalidFile("Formato não suportado. Escolha uma foto JPG, PNG, WebP ou um PDF.");
  }
  const file = original.type === type ? original : new File([original], original.name || "cupom", { type });
  if (file.size <= MAX_BYTES) return file;
  if (type === "application/pdf") throw invalidFile("O PDF ultrapassa 8 MB. Escolha um PDF menor.");
  if (type === "image/heic") throw invalidFile("A foto HEIC ultrapassa 8 MB. Salve em JPG ou escolha outra imagem.");
  let source: ImageBitmap | HTMLImageElement | undefined;
  let url: string | undefined;
  try {
    if (typeof createImageBitmap === "function") {
      source = await createImageBitmap(file, { imageOrientation: "from-image" });
    } else {
      url = URL.createObjectURL(file);
      const img = new Image();
      await new Promise<void>((resolve, reject) => { img.onload = () => resolve(); img.onerror = reject; img.src = url!; });
      source = img;
    }
    const width = source instanceof HTMLImageElement ? source.naturalWidth : source.width;
    const height = source instanceof HTMLImageElement ? source.naturalHeight : source.height;
    if (!width || !height) throw new Error("Empty dimensions");
    const scale = Math.min(1, 4096 / Math.max(width, height), Math.sqrt(12_000_000 / (width * height)));
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(width * scale));
    canvas.height = Math.max(1, Math.round(height * scale));
    const context = canvas.getContext("2d");
    if (!context) throw new Error("Canvas unavailable");
    context.fillStyle = "white";
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.drawImage(source, 0, 0, canvas.width, canvas.height);
    for (const quality of [0.9, 0.8, 0.7]) {
      const blob = await new Promise<Blob | null>(resolve => canvas.toBlob(resolve, "image/jpeg", quality));
      if (blob?.size && blob.size <= MAX_BYTES) return new File([blob], "cupom.jpg", { type: "image/jpeg" });
    }
  } catch {
    throw invalidFile("Não conseguimos preparar esta foto. Escolha uma imagem JPG pela galeria e tente novamente.");
  } finally {
    if (source && "close" in source) source.close();
    if (url) URL.revokeObjectURL(url);
  }
  throw invalidFile("A foto continua acima de 8 MB. Enquadre apenas a nota ou escolha uma imagem menor.");
}
