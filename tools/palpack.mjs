#!/usr/bin/env node
// palpack — Cache Pal content pipeline (D30/D31/D37; v2 grids per D51 wave 6).
//
//   node tools/palpack.mjs new <key> <id>        scaffold species/<key>.json
//   node tools/palpack.mjs validate              validate species/* and wardrobe/*
//   node tools/palpack.mjs publish               validate, hash, sign registry
//   node tools/palpack.mjs delist <key> "<why>"  stop distributing a species
//   node tools/palpack.mjs wardrobe-new <key>    scaffold wardrobe/<key>.json
//   node tools/palpack.mjs withdraw <key> "<why>"  stop selling a cosmetic
//
// publish needs the signing key: set PALPACK_KEY to the PRIVATE value from the
// key file Earl holds (base64url, 32 bytes). NEVER commit that value.
//
// Output layout (served verbatim by GitHub Pages):
//   packs/pack-<id>-<key>.<hash8>.json   content-hashed, immutable
//   cosmetics/cosmetics-<hash8>.json     content-hashed, immutable (D61)
//   registry.pub.json                    { payload: b64u(JSON bytes), signature: b64u }
//
// TWO content channels, and the split is deliberate (D61, closes B80):
//   species/   -> one pack per species. May carry cosmetics, but that path is
//                 FROZEN: generation 6's three pieces stay, nothing new joins them.
//   wardrobe/  -> one file per cosmetic, published as a single signed file that
//                 the registry payload names and SHA-256 pins. A cosmetic here
//                 shares no failure domain with any creature: a bad piece, a bad
//                 file, or a bad reader costs wardrobe items and nothing else.
//                 Generation 4 taught this the expensive way — one unparseable
//                 hat made two live species invisible.
//
// The registry is APPEND-ONLY: ids are never reused or remapped (the registry
// is the frozen table — DESIGN_DECISIONS D30). Delisting = "delisted": true.
// Cosmetic keys are append-only for a blunter reason: a piece that vanishes from
// wardrobe/ stops resolving for whoever BOUGHT it, so their Pal loses a hat it is
// wearing. Withdraw instead — it stays in the file and stops being sold.
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
else if (cmd === 'validate') {
  const { species, wardrobe } = validateAll();
  console.log(`✔ all valid — ${species.length} species, ${wardrobe.length} wardrobe piece(s)`);
}
else if (cmd === 'publish') publish();
else if (cmd === 'delist') delist(process.argv[3], process.argv.slice(4).join(' '));
else if (cmd === 'wardrobe-new') wardrobeScaffold(process.argv[3]);
else if (cmd === 'withdraw') withdraw(process.argv[3], process.argv.slice(4).join(' '));
else {
  console.error('Usage: palpack.mjs new <key> <id> | validate | publish');
  console.error('       palpack.mjs delist <key> "<reason>"          take down a species');
  console.error('       palpack.mjs wardrobe-new <key>               scaffold a cosmetic');
  console.error('       palpack.mjs withdraw <key> "<reason>"        stop selling a cosmetic');
  process.exit(2);
}

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
    //
    // FROZEN PATH. Generation 6's three pieces live here and always will, because
    // they are cached on real devices. New pieces belong in wardrobe/ (D61): a
    // cosmetic riding a species pack shares that species' failure domain, which is
    // what made generation 4 an outage, and a species delist silently withdraws
    // whatever pieces rode along with it.
    if (s.cosmetics !== undefined) {
      if (s.schema !== 'cachepal-pack-v2') fail(ctx, 'cosmetics require a v2 pack (v1 packs stay untouched for old-client compat)');
      if (!Array.isArray(s.cosmetics) || s.cosmetics.length === 0) fail(ctx, 'cosmetics, when present, must be a non-empty array');
      for (const c of s.cosmetics) {
        validateCosmetic(c, ctx, seenCosmeticKeys);
      }
    }

    all.push({ file: f, species: s });
  }
  if (all.length === 0) fail('species/', 'no species files found');
  // The wardrobe shares the cosmetic key namespace with the packs, so it is validated
  // with the SAME seen-set rather than separately — that is what makes a key claimed by
  // a pack unavailable to a wardrobe file and vice versa.
  return { species: all, wardrobe: validateWardrobe(seenCosmeticKeys) };
}

// ---- cosmetics ---------------------------------------------------------------

/**
 * The ONE cosmetic rulebook, shared by both delivery channels — pack-embedded
 * (v1.7, frozen) and the standalone wardrobe file (D61). One function, because two
 * copies of these rules would drift and the drift would land in signed content.
 * Mirrors CachePal.Core CosmeticDefinition.TryValidate exactly.
 */
function validateCosmetic(c, ctx, seenKeys) {
  const cc = `${ctx} cosmetic '${c?.key ?? '?'}'`;
  if (!/^[a-z][a-z0-9-]{2,31}$/.test(c.key ?? '')) fail(cc, 'key must be a lowercase slug (3-32, letter first)');
  if (typeof c.name !== 'string' || c.name.trim().length < 3 || c.name.trim().length > 24) fail(cc, 'name must be 3-24 chars');
  if (!['aura', 'scarf', 'hat', 'prop'].includes(c.slot)) fail(cc, 'slot must be aura/scarf/hat/prop');
  if (!['common', 'uncommon', 'rare', 'relic'].includes(c.tier)) fail(cc, 'tier must be common/uncommon/rare/relic');
  const price = c.price ?? 0, milestone = c.milestoneKey ?? '';
  if (!Number.isInteger(price) || price < 0 || price > 100000) fail(cc, 'price must be an integer 0..100000');
  if ((price > 0) === (milestone.length > 0)) fail(cc, 'exactly one acquisition path: price XOR milestoneKey');
  if (milestone.length > 0 && !/^[a-z][a-z0-9-]{2,47}$/.test(milestone)) fail(cc, 'milestoneKey must be a lowercase slug');
  // D59/D61: optional, default-false, and type-checked rather than coerced. A typo
  // ("wanders": "true") deserializes to nothing on the client, so the piece would
  // quietly ship as always-in-stock while its lore promised otherwise — or, worse for
  // `delisted`, would keep selling something the operator meant to withdraw.
  if (c.wanders !== undefined && typeof c.wanders !== 'boolean') fail(cc, 'wanders, when present, must be a boolean');
  if (c.delisted !== undefined && typeof c.delisted !== 'boolean') fail(cc, 'delisted, when present, must be a boolean');
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
  // Keys are content-unique FOREVER and across both channels: a key that appears in a
  // pack and in the wardrobe file would resolve differently on different clients
  // depending on which one they can read.
  if (seenKeys.has(c.key)) fail(cc, `duplicate cosmetic key '${c.key}' (keys are unique across packs AND wardrobe/)`);
  seenKeys.add(c.key);
}

function wardrobeFiles() {
  const dir = join(ROOT, 'wardrobe');
  if (!existsSync(dir)) return [];
  return readdirSync(dir).filter(f => f.endsWith('.json')).sort();
}

/**
 * Validates wardrobe/*.json — one piece per file, for the same reason species get one
 * file each: a diff that touches one piece should touch one file. Returns the pieces in
 * stable filename order, which is also the order they land in the signed file.
 */
function validateWardrobe(seenCosmeticKeys) {
  const pieces = [];
  for (const f of wardrobeFiles()) {
    const piece = JSON.parse(readFileSync(join(ROOT, 'wardrobe', f), 'utf8'));
    const ctx = `wardrobe/${f}`;
    // The filename IS the key. Not decoration: it is what makes "which file do I edit to
    // change Paper Admiral" answerable without grepping, and what stops two files from
    // silently claiming the same piece.
    if (piece.key !== f.replace(/\.json$/, '')) fail(ctx, `key '${piece.key}' must match the filename`);
    validateCosmetic(piece, ctx, seenCosmeticKeys);
    pieces.push(piece);
  }
  return pieces;
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

  const { species: all, wardrobe } = validateAll();
  mkdirSync(join(ROOT, 'packs'), { recursive: true });

  let generation = 1;
  let priorWardrobeKeys = [];
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
    // The wardrobe is append-only too (D61), and for a blunter reason than species: a
    // piece that disappears from the file stops resolving for the people who BOUGHT it,
    // so their Pal loses a hat it is wearing. Withdraw instead — the piece stays in the
    // file, stops being sold, and keeps rendering for its owners.
    if (prev.wardrobe?.file) {
      const priorPath = join(ROOT, prev.wardrobe.file);
      if (existsSync(priorPath)) {
        priorWardrobeKeys = (JSON.parse(readFileSync(priorPath, 'utf8')).cosmetics ?? []).map(c => c.key);
        for (const k of priorWardrobeKeys) {
          if (!wardrobe.some(c => c.key === k)) {
            console.error(`APPEND-ONLY VIOLATION: cosmetic '${k}' vanished from wardrobe/.`);
            console.error(`Owners would lose a piece they are wearing. Withdraw it instead:`);
            console.error(`  node tools/palpack.mjs withdraw ${k} "<reason>"`);
            process.exit(1);
          }
        }
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

  // The standalone wardrobe file (D61): content-hashed and immutable exactly like a
  // pack, and referenced from the signed payload so it inherits the registry's Ed25519
  // trust chain without a second signature to manage.
  let wardrobeRef;
  if (wardrobe.length > 0) {
    mkdirSync(join(ROOT, 'cosmetics'), { recursive: true });
    const fileBytes = Buffer.from(canonical({ schema: 'cachepal-cosmetics-v1', cosmetics: wardrobe }), 'utf8');
    const sha256 = createHash('sha256').update(fileBytes).digest('hex');
    const name = `cosmetics-${sha256.slice(0, 8)}.json`;
    writeFileSync(join(ROOT, 'cosmetics', name), fileBytes);
    wardrobeRef = { file: `cosmetics/${name}`, sha256 };
  }

  const payloadObj = {
    schema: 'cachepal-registry-v1',
    generation,
    publishedAt: new Date().toISOString(),
    species: entries,
    // Additive, and omitted entirely when there is no wardrobe file — an absent field
    // and a null one read the same to the client, but omitting it keeps the payload
    // honest about what this generation actually ships.
    ...(wardrobeRef ? { wardrobe: wardrobeRef } : {})
  };
  const payloadBytes = Buffer.from(canonical(payloadObj), 'utf8');
  const signature = sign(null, payloadBytes, privateKey);
  writeFileSync(join(ROOT, 'registry.pub.json'), JSON.stringify({
    payload: payloadBytes.toString('base64url'),
    signature: signature.toString('base64url')
  }, null, 2));

  const withdrawn = wardrobe.filter(c => c.delisted === true).length;
  const wardrobeNote = wardrobeRef
    ? `, wardrobe ${wardrobe.length} piece(s)${withdrawn > 0 ? ` (${withdrawn} withdrawn)` : ''}`
    : '';
  console.log(`✔ published generation ${generation}: ${entries.length} species${wardrobeNote}, signed.`);
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

/**
 * Stop offering a species (B62). This is the whole delist mechanism: the flag lives
 * INSIDE the signed registry payload, so a takedown is a re-sign, and re-signing needs
 * the operator key. No server can do it, which is why the Barn's admin action files an
 * intent for this command to execute rather than pretending to act on its own.
 *
 * What it does NOT do, and the runbook says the same: recall anything. A player who
 * already synced the pack keeps their Pal, permanently — the game's boot path registers
 * from the CACHED registry without filtering delisted entries, and cached packs are never
 * pruned. Delisting means "stop offering", never "remove".
 *
 * The species file stays. `publish` refuses if a registered id vanishes from species/
 * (append-only, D30), and this is the sanctioned alternative it points at.
 */
function delist(key, reason) {
  if (!key || !reason || reason.trim().length < 8) {
    console.error('Usage: palpack.mjs delist <key> "<reason>"');
    console.error('A reason is required and is not optional paperwork: it is what you paste');
    console.error('into DROPS.md and the moderation log, and what you will want in a year.');
    process.exit(2);
  }

  const file = join(ROOT, 'species', `${key}.json`);
  if (!existsSync(file)) {
    console.error(`No species/${key}.json — delisting works on the source, which stays put.`);
    process.exit(1);
  }

  const species = JSON.parse(readFileSync(file, 'utf8'));
  if (species.delisted === true) {
    console.log(`= ${key} (id ${species.id}) is already delisted — nothing to do.`);
    return;
  }

  species.delisted = true;
  // Public history stays NEUTRAL. The species timeline is player-facing; the why of a
  // takedown may name a complainant or a legal basis and belongs in the private
  // moderation log, not on a signed page served to everyone.
  species.history = [
    ...(Array.isArray(species.history) ? species.history : []),
    { date: new Date().toISOString().slice(0, 10), change: 'delisted', by: 'operator' }
  ];
  writeFileSync(file, `${JSON.stringify(species, null, 2)}\n`);

  console.log(`✔ ${key} (id ${species.id}) marked delisted in species/${key}.json`);
  console.log('');
  console.log('It is not live yet. Finish the takedown:');
  console.log('  node tools/palpack.mjs validate');
  console.log('  PALPACK_KEY=<PRIVATE> node tools/palpack.mjs publish');
  console.log(`  git add -A && git commit -m "content: delist ${key}" && git push`);
  console.log('');
  console.log('Then record the reason where it is private and durable (the moderation log):');
  console.log('  az storage entity insert --table-name BarnModerationLog --entity \\');
  console.log('    PartitionKey=mod RowKey=<inverted-ticks> Action=species-delisted \\');
  console.log(`    Target=species/${species.id} 'Reason=${reason.replace(/'/g, "''")}' At=<ISO8601Z>`);
  console.log('');
  console.log('And say so in DROPS.md, because a species going quiet with no note reads as a bug.');
  console.log('Reminder: players who already synced it keep their Pal. Delisting stops the');
  console.log('offering — it does not recall anything, and it cannot.');
}

// ---- wardrobe verbs (D61) ----------------------------------------------------

function wardrobeScaffold(key) {
  if (!/^[a-z][a-z0-9-]{2,31}$/.test(key ?? '')) {
    console.error('Usage: palpack.mjs wardrobe-new <key>   (lowercase slug, 3-32 chars, letter first)');
    console.error('Convention: <slot>-<name>, e.g. hat-paper-admiral, aura-moth-hour.');
    process.exit(2);
  }
  mkdirSync(join(ROOT, 'wardrobe'), { recursive: true });
  const file = join(ROOT, 'wardrobe', `${key}.json`);
  if (existsSync(file)) {
    console.error(`wardrobe/${key}.json already exists — keys are content-unique forever.`);
    process.exit(1);
  }
  const blank = '................';
  writeFileSync(file, `${JSON.stringify({
    key,
    name: 'TODO 3-24 chars',
    slot: 'hat',
    tier: 'common',
    price: 120,
    milestoneKey: '',
    wanders: false,
    lore: '',
    grid: Array.from({ length: 16 }, () => blank),
    palette: { W: '#FFFFFF' }
  }, null, 2)}\n`);

  console.log(`✔ scaffolded wardrobe/${key}.json`);
  console.log('');
  console.log('Rules worth knowing before you paint:');
  console.log('  · price XOR milestoneKey — exactly one acquisition path, never both.');
  console.log('  · price should match its tier: common 120, uncommon 350, rare 900, relic 2600.');
  console.log("    The shop prints the TIER's price as a heading, so an off-tier price lies to players.");
  console.log('  · 4-200 painted cells. Cosmetics decorate; they never replace the Pal.');
  console.log("  · '.' is transparent, '*' is the one shiny-reactive accent; everything else");
  console.log('    needs a #RRGGBB palette entry.');
  console.log('  · auras composite BEHIND the body and are occluded by it; scarves then hats');
  console.log('    paint in front. Check your art against the archetypes before signing.');
  console.log('');
  console.log('Then: node tools/palpack.mjs validate');
}

function withdraw(key, reason) {
  if (!key || !reason || reason.trim().length < 8) {
    console.error('Usage: palpack.mjs withdraw <key> "<reason>"');
    console.error('A reason is required for the same purpose as a species delist: it is what');
    console.error('you paste into the moderation log, and what you will want in a year.');
    process.exit(2);
  }

  const file = join(ROOT, 'wardrobe', `${key}.json`);
  if (!existsSync(file)) {
    console.error(`No wardrobe/${key}.json.`);
    console.error('If the piece rides a species pack instead (the frozen v1.7 path), edit that');
    console.error("pack's cosmetics entry directly — set \"delisted\": true on the piece.");
    process.exit(1);
  }

  const piece = JSON.parse(readFileSync(file, 'utf8'));
  if (piece.delisted === true) {
    console.log(`= ${key} is already withdrawn — nothing to do.`);
    return;
  }

  piece.delisted = true;
  writeFileSync(file, `${JSON.stringify(piece, null, 2)}\n`);

  console.log(`✔ ${key} marked withdrawn in wardrobe/${key}.json`);
  console.log('');
  console.log('It is not live yet. Finish it:');
  console.log('  node tools/palpack.mjs validate');
  console.log('  PALPACK_KEY=<PRIVATE> node tools/palpack.mjs publish');
  console.log(`  git add -A && git commit -m "content: withdraw ${key}" && git push`);
  console.log('');
  console.log('Then record the reason where it is private and durable:');
  console.log('  az storage entity insert --table-name BarnModerationLog --entity \\');
  console.log('    PartitionKey=mod RowKey=<inverted-ticks> Action=cosmetic-withdrawn \\');
  console.log(`    Target=cosmetic/${key} 'Reason=${reason.replace(/'/g, "''")}' At=<ISO8601Z>`);
  console.log('');
  console.log('What withdrawing does and does not do: the piece STAYS in the signed file, so');
  console.log('anyone who bought it keeps it and their Pal keeps wearing it. It leaves the shop,');
  console.log('and the buy path refuses it even on a stale page. Nothing is confiscated — the');
  console.log('file is append-only precisely so a takedown cannot strip a wardrobe.');
}
