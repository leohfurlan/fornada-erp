export function mascararWhatsApp(valor: string, regiao: string): string {
  const digitos = valor.replace(/\D/g, "");
  if (regiao !== "BR") return digitos.slice(0, 15);
  const telefone = digitos.slice(0, 11);
  if (telefone.length < 3) return telefone;
  const ddd = `(${telefone.slice(0, 2)}) `;
  return ddd + telefone.slice(2, 7) + (telefone.length > 7 ? `-${telefone.slice(7)}` : "");
}
