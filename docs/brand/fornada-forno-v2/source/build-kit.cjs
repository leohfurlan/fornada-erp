/* Identidade oficial Forno aberto: rosa e marrom aprovada em 07/10/2026. */
const fs = require('node:fs');
const path = require('node:path');
const sharp = require('C:/Users/Leonardo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const root = path.resolve(__dirname, '..');
const project = path.resolve(root, '../../..');
const palette = { rose: '#E7A0B3', brown: '#D8BDA6', outline: '#8E6D5A', ink: '#694B3D', cream: '#FFF7FA', primary: '#A34568', border: '#AD8870', white: '#FFFFFF' };
const geometry = JSON.parse(fs.readFileSync(path.join(__dirname, 'symbol-geometry.json'), 'utf8'));
const word = JSON.parse(fs.readFileSync(path.join(__dirname, 'wordmark-outlines.json'), 'utf8'));
const num = value => Number(value.toFixed(3));
const svg = (width, height, body, title) => `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-label="${title}"><title>${title}</title>${body}</svg>`;

function mark(fill, stroke, cx, cy, width, strokeWidth = 18) {
  const [x0, y0, x1, y1] = geometry.bounds;
  const scale = width / (x1 - x0);
  const tx = cx - (x0 + x1) * scale / 2;
  const ty = cy - (y0 + y1) * scale / 2;
  return `<g fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}" stroke-linejoin="round" transform="translate(${num(tx)} ${num(ty)}) scale(${num(scale)})">${geometry.paths.map(d => `<path d="${d}"/>`).join('')}</g>`;
}

function wordmark(fill, x, y, fontSize = 80) {
  const scale = fontSize / word.unitsPerEm;
  const [x0, , , y1] = word.bounds;
  return `<g fill="${fill}" transform="translate(${num(x - x0 * scale)} ${num(y + y1 * scale)}) scale(${num(scale)} ${num(-scale)})">${word.paths.map(d => `<path d="${d}"/>`).join('')}</g>`;
}

async function write(relative, source, pngRelative, width) {
  fs.writeFileSync(path.join(root, relative), source);
  if (pngRelative) await sharp(Buffer.from(source)).resize({ width }).png().toFile(path.join(root, pngRelative));
}

function ico(images) {
  const header = Buffer.alloc(6); header.writeUInt16LE(1, 2); header.writeUInt16LE(images.length, 4);
  let offset = 6 + 16 * images.length;
  const entries = images.map(({ size, buffer }) => {
    const entry = Buffer.alloc(16); entry[0] = size; entry[1] = size;
    entry.writeUInt16LE(1, 4); entry.writeUInt16LE(32, 6);
    entry.writeUInt32LE(buffer.length, 8); entry.writeUInt32LE(offset, 12);
    offset += buffer.length; return entry;
  });
  return Buffer.concat([header, ...entries, ...images.map(image => image.buffer)]);
}

async function main() {
  for (const dir of ['svg', 'png', 'favicon', 'app']) fs.mkdirSync(path.join(root, dir), { recursive: true });
  for (const [name, fill, stroke, text] of [
    ['primary', palette.rose, palette.outline, palette.outline],
    ['ink', palette.ink, palette.ink, palette.ink],
    ['white', palette.white, palette.white, palette.white],
  ]) {
    await write(`svg/simbolo-${name}.svg`, svg(256, 256, mark(fill, stroke, 128, 128, 200), 'Fornada — Forno aberto rosa e marrom'), `png/simbolo-${name}-1024.png`, 1024);
    await write(`svg/logo-horizontal-${name}.svg`, svg(512, 160, mark(fill, stroke, 80, 80, 112) + wordmark(text, 168, 49), 'Fornada — logo horizontal'), `png/logo-horizontal-${name}-2048.png`, 2048);
    await write(`svg/logo-vertical-${name}.svg`, svg(384, 360, mark(fill, stroke, 192, 145, 220) + wordmark(text, 57.6, 280), 'Fornada — logo vertical'), `png/logo-vertical-${name}-1536.png`, 1536);
  }
  // Contorno reforçado em 16/32 px; símbolo ligeiramente menor para não cortar a borda.
  const favicon = svg(256, 256, mark(palette.rose, palette.ink, 128, 128, 224, 64), 'Fornada favicon');
  await write('favicon/favicon.svg', favicon);
  const images = [];
  for (const size of [16, 32, 48, 64]) {
    const buffer = await sharp(Buffer.from(favicon)).resize(size, size).png().toBuffer();
    fs.writeFileSync(path.join(root, `favicon/favicon-${size}.png`), buffer);
    images.push({ size, buffer });
  }
  fs.writeFileSync(path.join(root, 'favicon/favicon.ico'), ico(images));
  const background = `<path fill="${palette.rose}" d="M0 0H256V256H0Z"/>`;
  const app = svg(256, 256, background + mark(palette.white, palette.ink, 128, 128, 172, 36), 'Fornada — aplicativo');
  await write('app/app-icon.svg', app);
  for (const size of [192, 512, 1024]) await sharp(Buffer.from(app)).resize(size, size).png().toFile(path.join(root, `app/app-icon-${size}.png`));
  await sharp(Buffer.from(app)).resize(180, 180).png().toFile(path.join(root, 'app/apple-touch-icon.png'));
  await write('app/app-maskable.svg', svg(256, 256, background + mark(palette.white, palette.ink, 128, 128, 128, 36), 'Fornada — ícone com área segura'), 'app/app-maskable-512.png', 512);
  await write('app/android-foreground.svg', svg(256, 256, mark(palette.white, palette.ink, 128, 128, 128, 36), 'Fornada — foreground Android'), 'app/android-foreground-432.png', 432);

  const label = (text, x, y, size = 16, fill = palette.ink) => `<text x="${x}" y="${y}" font-family="Segoe UI, sans-serif" font-size="${size}" fill="${fill}">${text}</text>`;
  const sheet = svg(1440, 920,
    `<rect width="1440" height="920" fill="${palette.cream}"/>` +
    label('FORNADA / FORNO ABERTO · REVISÃO DE PALETA', 64, 56, 13) +
    label('Rosa, marrom e contorno.', 64, 133, 56) +
    label('O mesmo forno. Uma presença mais delicada e definida.', 68, 179, 20) +
    `<rect x="64" y="220" width="600" height="370" rx="24" fill="white" stroke="${palette.border}" stroke-width="2"/>` +
    mark(palette.rose, palette.outline, 364, 390, 270) + label('SÍMBOLO COM CONTORNO MARROM', 92, 560, 13) +
    `<rect x="700" y="220" width="676" height="370" rx="24" fill="${palette.brown}" stroke="${palette.outline}" stroke-width="2"/>` +
    mark(palette.rose, palette.outline, 790, 395, 112) + wordmark(palette.ink, 875, 363, 82) + label('ASSINATURA · ROSA E MARROM', 730, 560, 13) +
    [['ROSA', palette.rose], ['MARROM CLARO', palette.brown], ['CONTORNO', palette.outline], ['ROSA DOS BOTÕES', palette.primary]].map(([name, color], i) => {
      const x = 64 + i * 210;
      return label(name, x, 657, 12) + `<rect x="${x}" y="680" width="180" height="56" rx="12" fill="${color}"/>` + label(color, x, 766, 16);
    }).join('') +
    `<rect x="982" y="645" width="148" height="148" rx="32" fill="${palette.rose}"/>` + mark(palette.white, palette.ink, 1056, 719, 104, 36) + label('ÍCONE DO APP', 982, 828, 13) +
    [16, 32, 48].map((size, i) => mark(palette.rose, palette.ink, 1188 + i * 76, 728, size * .875, 64) + label(`${size}px`, 1178 + i * 76, 784, 12)).join('') +
    label('Vetores preservados · Contornos definidos · Cores aplicadas à interface e aos ícones', 64, 864, 16),
    'Fornada — rosa e marrom');
  await write('prancha.svg', sheet, 'prancha.png', 1440);

  const runtime = path.join(project, 'frontend/public/brand/forno-v2');
  fs.mkdirSync(runtime, { recursive: true });
  const runtimeFiles = ['svg/logo-horizontal-primary.svg', 'svg/logo-horizontal-ink.svg', 'svg/logo-horizontal-white.svg', 'svg/simbolo-primary.svg', 'svg/simbolo-ink.svg', 'svg/simbolo-white.svg', 'favicon/favicon.svg', 'favicon/favicon.ico', 'app/apple-touch-icon.png', 'app/app-icon-192.png', 'app/app-icon-512.png', 'app/app-maskable-512.png'];
  for (const file of runtimeFiles) fs.copyFileSync(path.join(root, file), path.join(runtime, path.basename(file)));
  fs.writeFileSync(path.join(root, 'kit.json'), JSON.stringify({ version: '2.0', status: 'Identidade oficial aprovada: rosa e marrom com contorno', approved: true, approvedAt: '2026-10-07', date: '2026-10-07', colors: palette, geometry: 'Preservada da versão 1; apenas fill/stroke foram alterados.', contour: { logo: 18, favicon: 64, app: 36 }, wordmark: { font: word.font, outlined: true }, runtimeFiles }, null, 2));
  console.log(JSON.stringify({ version: '2.0', runtimeFiles: runtimeFiles.length, palette, preview: path.join(root, 'prancha.png') }));
}

main().catch(error => { console.error(error); process.exit(1); });
