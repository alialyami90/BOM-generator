// Bundles the prototype into one self-contained HTML file (CSS, JS and fonts inlined),
// for opening from a phone, a file manager or an email attachment.
// Usage: node tools/build-standalone.mjs [output.html]   (default: <repo>/out/ui-prototype.html)
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const proto = join(root, 'prototype');
const out = resolve(process.argv[2] ?? join(root, '..', '..', 'out', 'ui-prototype.html'));
const read = (p) => readFileSync(p, 'utf8');

let html = read(join(proto, 'index.html'));
const inlineCss = (file) => {
  const css = read(join(proto, file)).replace(/url\("\.\.\/fonts\/([^"]+\.woff2)"\)/g, (_, f) =>
    `url("data:font/woff2;base64,${readFileSync(join(root, 'fonts', f)).toString('base64')}")`);
  return `<style>\n${css}\n</style>`;
};
html = html.replace(/<link rel="stylesheet" href="([^"]+)">/g, (_, f) => inlineCss(f));
html = html.replace(/<script src="([^"]+)"><\/script>/g, (_, f) => `<script>\n${read(join(proto, f))}\n</script>`);
// The app is designed for a 1280 px window: on a phone, scale the page to fit instead of reflowing.
html = html.replace('<meta name="viewport" content="width=device-width, initial-scale=1">', '<meta name="viewport" content="width=1280">');

mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, html);
console.log(`wrote ${out} (${Math.round(html.length / 1024)} KB)`);
