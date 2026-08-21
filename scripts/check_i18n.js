#!/usr/bin/env node
'use strict';

// Verifies that the zh and en dictionaries in js/i18n.js have identical key
// sets, so translations can never silently drift apart.

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
if (!I18N || !I18N.zh || !I18N.en) {
  console.error('i18n.js did not expose window.I18N with zh and en dictionaries');
  process.exit(1);
}

const zh = Object.keys(I18N.zh).sort();
const en = Object.keys(I18N.en).sort();

const missingInEn = zh.filter((k) => !(k in I18N.en));
const missingInZh = en.filter((k) => !(k in I18N.zh));

let ok = true;
if (missingInEn.length) {
  ok = false;
  console.error(
    `Keys present in zh but missing in en (${missingInEn.length}):\n  ` +
      missingInEn.join('\n  ')
  );
}
if (missingInZh.length) {
  ok = false;
  console.error(
    `Keys present in en but missing in zh (${missingInZh.length}):\n  ` +
      missingInZh.join('\n  ')
  );
}

if (!ok) {
  console.error('\ni18n key sets are NOT symmetric.');
  process.exit(1);
}

console.log(`i18n OK: zh and en dictionaries each have ${zh.length} symmetric keys.`);
