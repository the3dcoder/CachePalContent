#!/usr/bin/env node
// palpack — Cache Pal content pipeline (D30/D31/D37; v2 grids per D51 wave 6).
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
//
// Pack schemas: "cachepal-pack-v1" for archetype-composed species (no custom
// grids), "cachepal-pack-v2" for species carrying gridBaby/gridTeen/gridAdult.
// The pairing is enforced BOTH ways: grids ⟺ v2. Grid-less species must stay
// v1 so game clients that predate v2 parsing (< app 1.6) keep accepting their
// packs; v2 species are invisible to those clients until they update, which
// only ever withholds a species they never had. Registry schema is unchanged.

import { createHash, createPrivateKey, sign } from 'crypto';
import { readFileSync, writeFileSync, readdirSync, existsSync, mkdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const LEGEND = new Set(['.', 'O', 'B', 'S', 'A', 'E', 'W', 'M', 'C', '#']);
// Custom body grids use the composer ROLE alphabet (SpeciesSubmission.AllowedChars
// in the game — X = feature role, no '#'). Distinct from the v1 feature LEGEND.
const GRID_LEGEND = new Set([...'.ABCEMOSWX']);
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
  const seenIds = new Set(), seenKeys = new Set(), seenCosmeticKeys = new Set();
  const all = [];
  for (const f of speciesFiles()) {
    const s = JSON.parse(readFileSync(join(ROOT, 'species', f), 'utf8'));
    const ctx = `species/${f}`;
    if (s.schema !== 'cachepal-pack-v1' && s.schema !== 'cachepal-pack-v2') {
      fail(ctx, 'schema must be cachepal-pack-v1 or cachepal-pack-v2');
    }
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

    // ---- v2: custom stage grids -------------------------------------------
    // Mirrors the game's PalSpriteGrids.IsValidCustomGrid (16×16 over the role
    // alphabet) plus the SpeciesSubmission quality floors. A present-but-invalid
    // grid makes the game silently degrade the WHOLE species to archetype art —
    // catching that here is the point of validating before signing.
    const gridStages = ['gridBaby', 'gridTeen', 'gridAdult'].filter(g => s[g] !== undefined);
    if (s.schema === 'cachepal-pack-v2' && gridStages.length !== 3) {
      fail(ctx, 'cachepal-pack-v2 requires all three of gridBaby/gridTeen/gridAdult');
    }
    if (s.schema === 'cachepal-pack-v1' && gridStages.length > 0) {
      fail(ctx, 'custom grids require schema cachepal-pack-v2 (grid-less species stay v1 for old-client compat)');
    }
    for (const stage of gridStages) {
      const grid = s[stage];
      if (!Array.isArray(grid) || grid.length !== 16) fail(ctx, `${stage} must be 16 rows`);
      let painted = 0, bodies = 0, outlines = 0;
      for (const row of grid) {
        if (typeof row !== 'string' || row.length !== 16) fail(ctx, `${stage} rows must be 16 chars`);
        for (const ch of row) {
          if (!GRID_LEGEND.has(ch)) fail(ctx, `${stage} char '${ch}' not in role alphabet .ABCEMOSWX`);
          if (ch !== '.') painted++;
          if (ch === 'B') bodies++;
          if (ch === 'O') outlines++;
        }
      }
      if (painted < 24) fail(ctx, `${stage} looks empty (${painted} painted, need ≥24)`);
      if (bodies < 8 || outlines < 4) fail(ctx, `${stage} needs a visible body (≥8 B) and outline (≥4 O)`);
    }

    // ---- v2: provenance (creator credit + living history) ------------------
    if (s.createdBy !== undefined && (typeof s.createdBy !== 'string' || !s.createdBy.trim())) {
      fail(ctx, 'createdBy, when present, must be a non-empty string (submitter barn name)');
    }
    if (s.history !== undefined) {
      if (!Array.isArray(s.history) || s.history.length === 0) fail(ctx, 'history, when present, must be a non-empty array');
      for (const h of s.history) {
        if (typeof h !== 'object' || h === null) fail(ctx, 'history entries must be objects');
        if (!/^\d{4}-\d{2}-\d{2}/.test(h.date ?? '')) fail(ctx, 'history entry date must start YYYY-MM-DD');
        if (typeof h.change !== 'string' || !h.change.trim()) fail(ctx, 'history entry change required');
        if (typeof h.by !== 'string' || !h.by.trim()) fail(ctx, 'history entry by required');
      }
    }
    if (s.premiereSeed !== undefined) {
      if (typeof s.premiereSeed !== 'string' || s.premiereSeed.length > 64
        || [...s.premiereSeed].some(c => c === '|' || c.charCodeAt(0) < 32)) {
        fail(ctx, 'premiereSeed must be ≤64 chars, no | or control chars');
      }
    }
    if (s.premiereDna !== undefined
      && !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(s.premiereDna)) {
      fail(ctx, 'premiereDna must be a GUID');
    }

    // ---- v1.7: cosmetics ride v2 species packs (additive field, never a new
    // schema string — a new string would make pre-1.7 clients drop the pack).
    // Rules mirror CachePal.Core CosmeticDefinition.TryValidate exactly.
    if (s.cosmetics !== undefined) {
      if (s.schema !== 'cachepal-pack-v2') fail(ctx, 'cosmetics require a v2 pack (v1 packs stay untouched for old-client compat)');
      if (!Array.isArray(s.cosmetics) || s.cosmetics.length === 0) fail(ctx, 'cosmetics, when present, must be a non-empty array');
      for (const c of s.cosmetics) {
        const cc = `${ctx} cosmetic '${c?.key ?? '?'}'`;
        if (!/^[a-z][a-z0-9-]{2,31}$/.test(c.key ?? '')) fail(cc, 'key must be a lowercase slug (3-32, letter first)');
        if (typeof c.name !== 'string' || c.name.trim().length < 3 || c.name.trim().length > 24) fail(cc, 'name must be 3-24 chars');
        if (!['aura', 'scarf', 'hat', 'prop'].includes(c.slot)) fail(cc, 'slot must be aura/scarf/hat/prop');
        if (!['common', 'uncommon', 'rare', 'relic'].includes(c.tier)) fail(cc, 'tier must be common/uncommon/rare/relic');
        const price = c.price ?? 0, milestone = c.milestoneKey ?? '';
        if (!Number.isInteger(price) || price < 0 || price > 100000) fail(cc, 'price must be an integer 0..100000');
        if ((price > 0) === (milestone.length > 0)) fail(cc, 'exactly one acquisition path: price XOR milestoneKey');
        if (milestone.length > 0 && !/^[a-z][a-z0-9-]{2,47}$/.test(milestone)) fail(cc, 'milestoneKey must be a lowercase slug');
        const lore = c.lore ?? '';
        if (lore.length > 200) fail(cc, 'lore must be 200 chars or fewer');
        if (c.tier === 'relic' && lore.trim().length === 0) fail(cc, 'relic pieces require lore');
        if (!Array.isArray(c.grid) || c.grid.length !== 16) fail(cc, 'grid must be 16 rows');
        let painted = 0;
        for (const row of c.grid) {
          if (typeof row !== 'string' || row.length !== 16) fail(cc, 'grid rows must be 16 chars');
          for (const ch of row) {
            if (ch === '.') continue;
            painted++;
            if (ch === '*') continue;
            if (!/^#[0-9A-Fa-f]{6}$/.test(c.palette?.[ch] ?? '')) fail(cc, `grid char '${ch}' needs a #RRGGBB palette entry`);
          }
        }
        if (painted < 4) fail(cc, 'art looks empty — paint at least 4 cells');
        if (painted > 200) fail(cc, 'cosmetics decorate, never replace — 200 painted cells max');
        if (seenCosmeticKeys.has(c.key)) fail(cc, `duplicate cosmetic key '${c.key}' across packs`);
        seenCosmeticKeys.add(c.key);
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
