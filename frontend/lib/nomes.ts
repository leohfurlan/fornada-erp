// Keep this rule equivalent to backend/domain/nomes.py.
const emoji = new RegExp("[\\u{1f000}-\\u{1faff}\\u2600-\\u27bf\\u2194-\\u2199\\u21a9-\\u21aa\\u231a-\\u231b\\u2328\\u23cf\\u23e9-\\u23f3\\u23f8-\\u23fa\\u24c2\\u25aa-\\u25ab\\u25b6\\u25c0\\u25fb-\\u25fe\\u2934-\\u2935\\u2b05-\\u2b07\\u2b1b-\\u2b1c\\u2b50\\u2b55\\u3030\\u303d\\u3297\\u3299\\u00a9\\u00ae\\u203c\\u2049\\u2122\\u2139\\ufe0e\\ufe0f\\u20e3]", "u");
const invisible = new RegExp("\\p{C}", "u");

export function nomeMaiusculo(value: string): string {
  return value.normalize("NFC").toUpperCase();
}

export function erroNome(value: string): string | null {
  if (emoji.test(value)) return "O nome não pode conter emojis.";
  if (invisible.test(value)) return "O nome não pode conter quebras de linha ou caracteres invisíveis.";
  const nome = nomeMaiusculo(value).trim().replace(/\s+/g, " ");
  if (Array.from(nome).length < 1 || Array.from(nome).length > 200) return "Informe um nome de 1 a 200 caracteres.";
  return null;
}
