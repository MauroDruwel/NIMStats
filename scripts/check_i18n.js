#!/usr/bin/env node
'use strict';

// Verifies that every language dictionary in js/i18n.js has the same key set
// as English, so translations can never silently drift apart.

const fs = require('fs');
const path = require('path');

const file = path.join(__dirname, '..', 'js', 'i18n.js');
const code = fs.readFileSync(file, 'utf8');

// Load i18n.js in a minimal browser-like sandbox (no DOM needed at load time).
const sandboxWindow = {};
const sandboxLocalStorage = { getItem: () => null, setItem: () => {} };
new Function('window', 'localStorage', 'document', code)(
  sandboxWindow,
  sandboxLocalStorage,
  {}
);

const I18N = sandboxWindow.I18N;
if (!I18N || !I18N.en) {
  console.error('i18n.js did not expose window.I18N with an en dictionary');
  process.exit(1);
}

const langs = Object.keys(I18N);
const reference = Object.keys(I18N.en).sort();
console.log(`Reference (en) keys: ${reference.length}`);
console.log(`Languages found: ${langs.join(', ')}`);

let ok = true;
for (const lang of langs) {
  const keys = Object.keys(I18N[lang]).sort();
  if (keys.length !== reference.length) {
    ok = false;
    console.error(`\n[${lang}] key count mismatch: ${keys.length} vs ${reference.length}`);
  }
  const missing = reference.filter((k) => !(k in I18N[lang]));
  const extra = keys.filter((k) => !(k in I18N.en));
  if (missing.length) {
    ok = false;
    console.error(`[${lang}] missing keys (${missing.length}):\n  ` + missing.join('\n  '));
  }
  if (extra.length) {
    ok = false;
    console.error(`[${lang}] extra keys (${extra.length}):\n  ` + extra.join('\n  '));
  }
}

if (!ok) {
  console.error('\ni18n key sets are NOT symmetric.');
  process.exit(1);
}

console.log(`\ni18n OK: ${langs.length} languages each have ${reference.length} symmetric keys.`);
