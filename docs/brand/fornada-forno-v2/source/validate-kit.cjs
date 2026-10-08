const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const sharp = require('C:/Users/Leonardo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const root = path.resolve(__dirname, '..');
const project = path.resolve(root, '../../..');
const kit = JSON.parse(fs.readFileSync(path.join(root, 'kit.json'), 'utf8'));

async function main() {
  const checks = [];
  const previous = JSON.parse(fs.readFileSync(path.join(root, '../fornada-forno-v1/source/symbol-geometry.json'), 'utf8'));
  const current = JSON.parse(fs.readFileSync(path.join(__dirname, 'symbol-geometry.json'), 'utf8'));
  assert.deepEqual(current.paths, previous.paths);
  checks.push('Geometria original preservada');
  for (const file of kit.runtimeFiles) {
    const source = fs.readFileSync(path.join(root, file));
    assert.deepEqual(source, fs.readFileSync(path.join(project, 'frontend/public/brand/forno-v2', path.basename(file))));
    if (file.endsWith('.svg')) {
      const text = source.toString();
      assert(!/<(?:image|script|text)\b/.test(text));
      assert(text.includes('stroke='));
      assert(!text.includes('#D95D39'));
    }
    checks.push(`Cópia do frontend e vetor: ${file}`);
  }
  for (const [file, size] of [['app/apple-touch-icon.png', 180], ['app/app-icon-192.png', 192], ['app/app-icon-512.png', 512], ['app/app-maskable-512.png', 512], ['favicon/favicon-16.png', 16], ['favicon/favicon-32.png', 32], ['favicon/favicon-48.png', 48], ['favicon/favicon-64.png', 64]]) {
    const metadata = await sharp(path.join(root, file)).metadata();
    assert.equal(metadata.width, size); assert.equal(metadata.height, size);
    checks.push(`Dimensão correta: ${file}`);
  }
  const ico = fs.readFileSync(path.join(root, 'favicon/favicon.ico'));
  assert.equal(ico.readUInt16LE(2), 1); assert.equal(ico.readUInt16LE(4), 4);
  checks.push('ICO com quatro tamanhos');
  const { data, info } = await sharp(path.join(root, 'app/app-maskable-512.png')).removeAlpha().raw().toBuffer({ resolveWithObject: true });
  let maxRadius = 0;
  for (let y = 0; y < info.height; y++) for (let x = 0; x < info.width; x++) {
    const i = (y * info.width + x) * 3;
    if (Math.abs(data[i] - 231) + Math.abs(data[i + 1] - 160) + Math.abs(data[i + 2] - 179) > 24) maxRadius = Math.max(maxRadius, Math.hypot(x + .5 - 256, y + .5 - 256));
  }
  assert(maxRadius <= 512 * .4);
  checks.push('Símbolo e contorno dentro da área segura maskable');
  const result = { date: '2026-10-07', passed: true, checks, maskableMaxRadius: maxRadius, safeRadius: 512 * .4 };
  fs.writeFileSync(path.join(root, 'validacao.json'), JSON.stringify(result, null, 2));
  console.log(JSON.stringify({ passed: true, checks: checks.length, maxRadius }));
}
main().catch(error => { console.error(error); process.exit(1); });
