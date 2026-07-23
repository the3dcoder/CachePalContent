#!/usr/bin/env node
// palpack — Cache Pal content pipeline (D30/D31/D37).
//
//   node tools/palpack.mjs new <key> <id>        scaffold species/<key>.json
//   node tools/palpack.mjs validate              validate every species/*.json
//   node tools/palpack.mjs publish               validate, hash packs, sign registry
//
// publish needs the signing key: set PALPACK_KEY to the PRIVATE value from the
// key file Earl holds (base64url, 32 bytes). NEVER commit that value.
//
// Output layout (served verbatim by GitHub Pages):
//   packs/pack-<id>-<key>.<hash8>.json   content-hashed, immutable
//   registry.pub.json                    { payload: b64u(JSON bytes), signature: b64u }
//
// The registry is APPEND-ONLY: ids are never reused or remapped (the registry
// is the frozen table — DESIGN_DECISIONS D30). Delisting = "delisted": true.

import { createHash, createPrivateKey, sign } from 'crypto';
import { readFileSync, writeFileSync, readdirSync, existsSync, mkdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const LEGEND = new Set(['.', 'O', 'B', 'S', 'A', 'E', 'W', 'M', 'C', '#']);
const ARCHETYPES = new Set(['blob', 'quad', 'wisp', 'shell', 'fish', 'avian', 'biped', 'jelly', 'serpent']);
const BUILTIN_MAX_ID = 13; // ids 0-13 are compiled into the app — never here

const cmd = process.argv[2];
if (cmd === 'new') scaffold(process.argv[3], Number(process.argv[4]));
else if (cmd === 'validate') { validateAll(); console.log('✔ all species valid'); }
else if (cmd === 'publish') publish();
else { console.error('Usage: palpack.mjs new <key> <id> | validate | publish'); process.exit(2); }

function speciesFiles() {
  const dir = join(ROOT, 'species');
  if (!existsSync(dir)) return [];
  return readdirSync(dir).filter(f => f.endsWith('.json')).sort();
}

function fail(file, msg) { console.error(`INVALID ${file}: ${msg}`); process.exit(1); }

function validateAll() {
  const seenIds = new Set(), seenKeys = new Set();
  const all = [];
  for (const f of speciesFiles()) {
    const s = JSON.parse(readFileSync(join(ROOT, 'species', f), 'utf8'));
    const ctx = `species/${f}`;
    if (s.schema !== 'cachepal-pack-v1') fail(ctx, 'schema must be cachepal-pack-v1');
    if (!Number.isInteger(s.id) || s.id <= BUILTIN_MAX_ID || s.id > 65535) fail(ctx, `id must be ${BUILTIN_MAX_ID + 1}..65535`);
    if (seenIds.has(s.id)) fail(ctx, `duplicate id ${s.id}`); seenIds.add(s.id);
    if (!/^[a-z][a-z0-9-]{2,23}$/.test(s.key)) fail(ctx, 'key must be lowercase slug (3-24 chars)');
    if (seenKeys.has(s.key)) fail(ctx, `duplicate key ${s.key}`); seenKeys.add(s.key);
    for (const field of ['name', 'description', 'hungryFor', 'babyDescription', 'teenDescription', 'adultDescription', 'credit']) {
      if (typeof s[field] !== 'string' || !s[field].trim()) fail(ctx, `${field} required`);
    }
    for (const c of ['baseColor', 'shinyColor']) {
      if (!/^#[0-9A-Fa-f]{6}$/.test(s[c])) fail(ctx, `${c} must be #RRGGBB`);
    }
    if (!ARCHETYPES.has(s.bodyArchetype)) fail(ctx, `bodyArchetype must be one of ${[...ARCHETYPES].join('/')}`);
    if (!Array.isArray(s.statBias) || s.statBias.length !== 6 || !s.statBias.every(n => Number.isInteger(n) && n >= -5 && n <= 8)) {
      fail(ctx, 'statBias must be 6 ints in -5..8');
    }
    if (s.statBias.reduce((a, b) => a + b, 0) > 10) fail(ctx, 'statBias total must be <= 10 (fairness cap)');
    if (!Array.isArray(s.needDecayBias) || s.needDecayBias.length !== 5 || !s.needDecayBias.every(n => typeof n === 'number' && n >= 0.6 && n <= 1.3)) {
      fail(ctx, 'needDecayBias must be 5 numbers in 0.6..1.3');
    }
    if (s.weight !== undefined && (!Number.isInteger(s.weight) || s.weight < 0 || s.weight > 10000)) {
      fail(ctx, 'weight must be an integer 0..10000 (spawn odds; 0 = retired from wild rolls)');
    }
    if (s.feature !== undefined) {
      if (!Array.isArray(s.feature) || s.feature.length !== 16) fail(ctx, 'feature must be 16 rows');
      for (const row of s.feature) {
        if (typeof row !== 'string' || row.length !== 16) fail(ctx, 'feature rows must be 16 chars');
        for (const ch of row) if (!LEGEND.has(ch)) fail(ctx, `feature char '${ch}' not in legend`);
      }
    }
    all.push({ file: f, species: s });
  }
  if (all.length === 0) fail('species/', 'no species files found');
  return all;
}

function canonical(obj) {
  // Stable stringify: sorted keys, no whitespace — byte-stable across runs.
  if (Array.isArray(obj)) return '[' + obj.map(canonical).join(',') + ']';
  if (obj && typeof obj === 'object') {
    return '{' + Object.keys(obj).sort().map(k => JSON.stringify(k) + ':' + canonical(obj[k])).join(',') + '}';
  }
  return JSON.stringify(obj);
}

function publish() {
  const key = process.env.PALPACK_KEY;
  if (!key) { console.error('Set PALPACK_KEY to the PRIVATE signing value (base64url).'); process.exit(2); }
  const privDer = Buffer.concat([
    Buffer.from('302e020100300506032b657004220420', 'hex'), // PKCS#8 Ed25519 prefix
    Buffer.from(key, 'base64url')
  ]);
  const privateKey = createPrivateKey({ key: privDer, format: 'der', type: 'pkcs8' });

  const all = validateAll();
  mkdirSync(join(ROOT, 'packs'), { recursive: true });

  let generation = 1;
  const prior = join(ROOT, 'registry.pub.json');
  if (existsSync(prior)) {
    const prev = JSON.parse(Buffer.from(JSON.parse(readFileSync(prior, 'utf8')).payload, 'base64url').toString('utf8'));
    generation = prev.generation + 1;
    for (const p of prev.species) {
      if (!all.some(a => a.species.id === p.id)) {
        console.error(`APPEND-ONLY VIOLATION: id ${p.id} (${p.key}) vanished from species/. Delist it instead.`);
        process.exit(1);
      }
    }
  }

  const entries = [];
  for (const { species: s } of all.sort((a, b) => a.species.id - b.species.id).map(x => x)) {
    const packBytes = Buffer.from(canonical(s), 'utf8');
    const sha256 = createHash('sha256').update(packBytes).digest('hex');
    const packName = `pack-${s.id}-${s.key}.${sha256.slice(0, 8)}.json`;
    writeFileSync(join(ROOT, 'packs', packName), packBytes);
    entries.push({
      id: s.id, key: s.key, name: s.name, credit: s.credit,
      pack: `packs/${packName}`, sha256, delisted: s.delisted === true
    });
  }

  const payloadObj = {
    schema: 'cachepal-registry-v1',
    generation,
    publishedAt: new Date().toISOString(),
    species: entries
  };
  const payloadBytes = Buffer.from(canonical(payloadObj), 'utf8');
  const signature = sign(null, payloadBytes, privateKey);
  writeFileSync(join(ROOT, 'registry.pub.json'), JSON.stringify({
    payload: payloadBytes.toString('base64url'),
    signature: signature.toString('base64url')
  }, null, 2));
  console.log(`✔ published generation ${generation}: ${entries.length} species, signed.`);
}

function scaffold(key, id) {
  if (!key || !Number.isInteger(id)) { console.error('Usage: palpack.mjs new <key> <id>'); process.exit(2); }
  mkdirSync(join(ROOT, 'species'), { recursive: true });
  const path = join(ROOT, 'species', `${key}.json`);
  if (existsSync(path)) { console.error(`${path} already exists`); process.exit(1); }
  writeFileSync(path, JSON.stringify({
    schema: 'cachepal-pack-v1', id, key,
    name: key[0].toUpperCase() + key.slice(1),
    description: 'TODO', credit: 'TODO',
    baseColor: '#888888', shinyColor: '#CCCCCC', bodyArchetype: 'blob',
    statBias: [0, 0, 0, 0, 0, 0], hungryFor: 'TODO',
    needDecayBias: [1, 1, 1, 1, 1],
    babyDescription: 'TODO', teenDescription: 'TODO', adultDescription: 'TODO'
  }, null, 2));
  console.log(`scaffolded ${path}`);
}
