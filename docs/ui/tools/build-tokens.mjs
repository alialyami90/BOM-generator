// Generates prototype/tokens.css from tokens.json.
// Usage: node tools/build-tokens.mjs        (writes the file)
//        node tools/build-tokens.mjs --check (exit 1 if the file is stale)
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const tokens = JSON.parse(readFileSync(join(root, 'tokens.json'), 'utf8'));
const outPath = join(root, 'prototype', 'tokens.css');

const get = (path) => path.split('.').reduce((n, k) => n?.[k], tokens);
const isToken = (n) => n && typeof n === 'object' && '$value' in n;

function resolve(value) {
  if (typeof value === 'string') {
    const m = value.match(/^\{(.+)\}$/);
    if (m) {
      const t = get(m[1]);
      if (!isToken(t)) throw new Error(`Unresolved reference ${value}`);
      return resolve(t.$value);
    }
  }
  return value;
}

function css(token) {
  const v = resolve(token.$value);
  switch (token.$type) {
    case 'fontFamily':
      return v.map((f) => (/\s/.test(f) ? `"${f}"` : f)).join(', ');
    case 'cubicBezier':
      return `cubic-bezier(${v.join(', ')})`;
    case 'shadow':
      return `${v.offsetX} ${v.offsetY} ${v.blur} ${v.spread} ${v.color}`;
    default:
      return String(v);
  }
}

const kebab = (s) => s.replace(/([a-z0-9])([A-Z])/g, '$1-$2').toLowerCase();

function walk(node, prefix, out) {
  for (const [key, child] of Object.entries(node)) {
    if (key.startsWith('$')) continue;
    if (isToken(child)) {
      if (child.$type === 'typography') {
        const v = child.$value;
        const base = `--${prefix}${kebab(key)}`;
        out.push([`${base}-font`, `${resolve(v.fontFamily).map((f) => (/\s/.test(f) ? `"${f}"` : f)).join(', ')}`]);
        out.push([`${base}-size`, v.fontSize]);
        out.push([`${base}-weight`, String(v.fontWeight)]);
        out.push([`${base}-leading`, String(v.lineHeight)]);
        out.push([`${base}-tracking`, v.letterSpacing]);
      } else {
        out.push([`--${prefix}${kebab(key)}`, css(child)]);
      }
    } else {
      walk(child, `${prefix}${kebab(key)}-`, out);
    }
  }
}

function block(selector, pairs) {
  return `${selector} {\n${pairs.map(([k, v]) => `  ${k}: ${v};`).join('\n')}\n}\n`;
}

const shared = [];
walk(tokens.primitive.fontFamily, 'font-', shared);
walk(tokens.typography.fontWeight, 'weight-', shared);
walk(tokens.typography.scale, 'type-', shared);
walk(tokens.space, 'space-', shared);
walk(tokens.size, 'size-', shared);
walk(tokens.radius, 'radius-', shared);
walk(tokens.border, 'border-', shared);
walk(tokens.motion.duration, 'duration-', shared);
walk(tokens.motion.easing, 'ease-', shared);
shared.push(['--color-highlight-yellow', css(tokens.primitive.color.highlight.yellow)]);

const theme = (mode) => {
  const out = [];
  walk(tokens.semantic[mode].color, 'color-', out);
  walk(tokens.semantic[mode].shadow, 'shadow-', out);
  return out;
};

const header = '/* Generated from ../tokens.json by tools/build-tokens.mjs. Do not edit. */\n';
const body =
  header +
  block(':root', shared) +
  block(':root, :root[data-theme="light"]', theme('light')) +
  '@media (prefers-color-scheme: dark) {\n' +
  block(':root:not([data-theme="light"])', theme('dark')).replace(/^/gm, '  ').replace(/\n  $/, '\n') +
  '}\n' +
  block(':root[data-theme="dark"]', theme('dark'));

if (process.argv.includes('--check')) {
  let current = '';
  try { current = readFileSync(outPath, 'utf8'); } catch {}
  if (current !== body) { console.error('prototype/tokens.css is stale; run node tools/build-tokens.mjs'); process.exit(1); }
  console.log('tokens.css is up to date');
} else {
  writeFileSync(outPath, body);
  console.log(`wrote ${outPath}`);
}
