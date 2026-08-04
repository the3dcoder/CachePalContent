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
// publish env, all optional, all deliberate rather than convenient (B205):
//   PALPACK_ALLOW_GENESIS=1   there is genuinely no previous registry (first publish ever)
//   PALPACK_SKIP_FRESHNESS=1  publish without confirming the clone against the live channel
//   PALPACK_REGISTRY_URL      where the live registry lives (default: the compiled URL below)
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
// APPEND-ONLY IS PER CHANNEL, AND THE CHANNEL SET IS DERIVED (B205). `publish`
// re-signs the WHOLE registry every run, so any channel this run fails to emit is
// UNPUBLISHED for everyone who owns something in it. The guard therefore reads the
// channel set out of the PREVIOUS PAYLOAD'S OWN KEYS — every key holding a
// {file, sha256} ref is a channel — rather than checking a named list. A named list
// of two is exactly how the backgrounds channel went unguarded from the day it
// shipped, and it is how the fourth channel would go unguarded too. A channel
// present in generation N and absent in N+1 is a DELETION and is refused; so is an
// entry inside one. Growth is fine: a channel that has never existed may appear.
//
// A guard is only as good as its baseline, and the baseline is this clone (B205's
// actual incident: a clone at generation 7 while the channel served 8, whose palpack
// predated backgrounds entirely — its append-only guard had nothing to compare
// because ITS previous payload had no backgrounds key either). So `publish` also
// refuses unless this clone's registry.pub.json is byte-for-byte what the live
// channel is serving right now. The two halves are not redundant: the append-only
// guard cannot see a deletion that is invisible in a stale baseline, and freshness
// alone would not stop a deletion made deliberately on a current one.
//
// Pack schemas: "cachepal-pack-v1" for archetype-composed species (no custom
// grids), "cachepal-pack-v2" for species carrying gridBaby/gridTeen/gridAdult.
// The pairing is enforced BOTH ways: grids ⟺ v2. Grid-less species must stay
// v1 so game clients that predate v2 parsing (< app 1.6) keep accepting their
// packs; v2 species are invisible to those clients until they update, which
// only ever withholds a species they never had. Registry schema is unchanged.

import { execFileSync } from 'node:child_process';
import { createHash, createPrivateKey, sign } from 'crypto';
import { readFileSync, writeFileSync, readdirSync, existsSync, mkdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const LEGEND = new Set(['.', 'O', 'B', 'S', 'A', 'E', 'W', 'M', 'C', '#']);
// Custom body grids use the composer ROLE alphabet (SpeciesSubmission.AllowedChars
// in the game — X = feature role, no '#'). Distinct from the v1 feature LEGEND.
const GRID_LEGEND = new Set([...'.ABCEMOSWX']);
// The ELEVEN body archetypes the shipped client knows. `bloom` and `crawler` arrived with B25 in
// game release v1.25.0 (2026-07-26) and this list was not updated with them, so for nine days the
// content tooling refused two body plans the game had been drawing perfectly well — B340. Adding
// them is safe only because v1.25.0 is confirmed as the floor build in the wild: an archetype this
// list allows but a client does not know makes `TryRegisterPack` drop the WHOLE PACK, leaving every
// Pal of that species a dormant mystery egg rather than falling back to a body.
//
// So this constant is not a preference — it is a claim about what is installed on real devices, and
// it may only grow after a release carrying the new archetype is the floor. `pack-agreement.mjs`
// now holds it from the other side (B341): it asserts palpack ACCEPTS every archetype the client
// knows, which is the direction that was missing when this drifted.
// Discovery rule keys the shipped client can satisfy. Grows only when the game ships one and
// that release is the floor in the wild — the same rule the archetype set carries, written out
// there in full.
const OBTAIN_RULES = new Set([
  'always', 'morning', 'evening-night', 'weekend', 'winter', 'summer', 'spring', 'autumn',
  'time-noon', 'weather-rain', 'weather-snow', 'weather-clear', 'gps-anywhere', 'gps-water',
  'milestone-pals-5', 'milestone-perfect-7', 'milestone-battles-10',
  'milestone-expeditions-8', 'milestone-expeditions-30',
]);

const ARCHETYPES = new Set([
  'blob', 'quad', 'wisp', 'shell', 'fish', 'avian', 'biped', 'jelly', 'serpent', 'bloom', 'crawler',
]);
const BUILTIN_MAX_ID = 13; // ids 0-13 are compiled into the app — never here
// The live channel, same casing as the client's compiled ContentSyncService.DefaultBaseUrl
// (GitHub Pages project paths are case-sensitive; this casing is the verified-working one).
const LIVE_BASE = 'https://the3dcoder.github.io/CachePalContent';

const cmd = process.argv[2];
if (cmd === 'new') scaffold(process.argv[3], Number(process.argv[4]));
else if (cmd === 'validate') {
  const { species, wardrobe } = validateAll();
  console.log(`✔ all valid — ${species.length} species, ${wardrobe.length} wardrobe piece(s)`);
}
else if (cmd === 'publish') await publish(); // async: the freshness gate reads the live channel
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
  // The discovery rules the shipped client knows (B345/D227). Same contract as ARCHETYPES above,
  // and for the same reason B340 exists: a rule key this list allows but a client does not know
  // normalises to "always" there, so a species meant to be EARNED would arrive on day one for
  // everybody and nothing would say so. `pack-agreement.mjs` holds both directions.
  if (s.obtainRule !== undefined && !OBTAIN_RULES.has(s.obtainRule)) {
    fail(ctx, `obtainRule must be one of ${[...OBTAIN_RULES].join('/')}`);
  }
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

// ── B350: THE TREE MUST BE THE TREE THE OPERATOR MEANT TO SIGN ──────────────────────────────────
//
// On 2026-08-04 this tool signed a generation containing SIX species while the operator was
// publishing EIGHTEEN. Nothing was wrong with the tool: the session's working copy was reverted
// underneath it, between `validate` (which counted 18 and passed) and `publish` (which read 6 and
// signed them). Every existing gate was satisfied, because every existing gate asks whether the
// tree is INTERNALLY consistent and current against the live registry — and a smaller tree is both.
//
// Nothing reached production that day only because the push had not happened yet. That is luck, and
// luck is not a control on an append-only, publicly cached, signed artifact.
//
// So: the operator PINS what they are signing, and this refuses if the tree has moved. The commit
// is the pin rather than a count, because a count of eighteen can be satisfied by the wrong
// eighteen, while a revert always moves HEAD. The count is kept as a second term because an
// uncommitted deletion does not move HEAD at all.
//
// Checked TWICE — once on entry so a wrong pin costs nothing, and again immediately before the
// first byte is written, because the whole point is that the tree can move mid-run.
function assertPinnedTree(speciesCount, when) {
  const pinCommit = process.env.PALPACK_EXPECT_COMMIT;
  const pinCount = process.env.PALPACK_EXPECT_SPECIES;
  if (!pinCommit && !pinCount) {
    console.error('REFUSING TO SIGN AN UNPINNED TREE.');
    console.error('  Set PALPACK_EXPECT_COMMIT to the commit you mean to publish (git rev-parse HEAD),');
    console.error('  and PALPACK_EXPECT_SPECIES to how many species it should contain.');
    console.error('  Both are cheap; a wrong generation is permanent (B350).');
    process.exit(2);
  }
  if (pinCount !== undefined && Number(pinCount) !== speciesCount) {
    console.error(`TREE MOVED (${when}): expected ${pinCount} species, found ${speciesCount}.`);
    console.error('  Refusing rather than signing a set the operator did not choose.');
    process.exit(1);
  }
  if (pinCommit) {
    let head = '';
    try {
      head = execFileSync('git', ['-C', ROOT, 'rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
    } catch (err) {
      // Narrow deliberately. A bare `catch` here reported a missing `execFileSync` import as
      // "cannot read HEAD" — a programming error wearing an environment error's clothes, which
      // made the commit pin look like it was working when it had never run once. Anything that is
      // not git failing is re-thrown.
      if (err instanceof ReferenceError || err instanceof TypeError) throw err;
      console.error(`CANNOT READ HEAD (${when}) — a pinned publish needs a git checkout it can resolve.`);
      console.error(`  ${String(err.message).split('\n')[0]}`);
      process.exit(1);
    }
    if (head !== pinCommit) {
      console.error(`TREE MOVED (${when}): expected commit ${pinCommit}, HEAD is ${head}.`);
      console.error('  The working copy is not the one that was reviewed. Refusing.');
      process.exit(1);
    }
  }
}

async function publish() {
  const key = process.env.PALPACK_KEY;
  if (!key) { console.error('Set PALPACK_KEY to the PRIVATE signing value (base64url).'); process.exit(2); }
  const privDer = Buffer.concat([
    Buffer.from('302e020100300506032b657004220420', 'hex'), // PKCS#8 Ed25519 prefix
    Buffer.from(key, 'base64url')
  ]);
  const privateKey = createPrivateKey({ key: privDer, format: 'der', type: 'pkcs8' });

  const { species: all, wardrobe } = validateAll();
  assertPinnedTree(all.length, 'on entry');

  // Gate 1 (B205): what are we appending TO? Both halves refuse rather than warn.
  const prev = readBaseline();
  await assertCloneIsCurrent(prev);
  const generation = prev ? prev.generation + 1 : 1;

  // Assemble everything this generation would ship — packs, channel files, the payload —
  // WITHOUT writing a byte. The append-only guard then compares the previous payload against
  // the payload that is actually about to be signed, rather than against a proxy for it, and
  // a refusal leaves the working tree exactly as it found it.
  // The tree can move between the read above and the write below — it did, once.
  assertPinnedTree(all.length, 'before writing');

  const entries = [];
  const packWrites = [];
  for (const { species: s } of all.slice().sort((a, b) => a.species.id - b.species.id)) {
    const packBytes = Buffer.from(canonical(s), 'utf8');
    const sha256 = createHash('sha256').update(packBytes).digest('hex');
    const packName = `pack-${s.id}-${s.key}.${sha256.slice(0, 8)}.json`;
    packWrites.push({ path: join(ROOT, 'packs', packName), bytes: packBytes });
    entries.push({
      id: s.id, key: s.key, name: s.name, credit: s.credit,
      pack: `packs/${packName}`, sha256, delisted: s.delisted === true
    });
  }

  // Every signed FILE channel this generation ships, as a descriptor: the payload ref, the
  // file's parsed content (so the guard derives entries the same way on both sides of the
  // comparison), and the bytes to write if there are any. Building a channel is necessarily
  // per-channel work — you cannot derive how to assemble a backgrounds file from a key name.
  // GUARDING one is not: see assertAppendOnly, which never learns these names.
  const channels = [];

  // The standalone wardrobe file (D61): content-hashed and immutable exactly like a
  // pack, and referenced from the signed payload so it inherits the registry's Ed25519
  // trust chain without a second signature to manage.
  if (wardrobe.length > 0) {
    const content = { schema: 'cachepal-cosmetics-v1', cosmetics: wardrobe };
    const fileBytes = Buffer.from(canonical(content), 'utf8');
    const sha256 = createHash('sha256').update(fileBytes).digest('hex');
    const name = `cosmetics-${sha256.slice(0, 8)}.json`;
    channels.push({
      name: 'wardrobe', content, bytes: fileBytes,
      dir: join(ROOT, 'cosmetics'), path: join(ROOT, 'cosmetics', name),
      ref: { file: `cosmetics/${name}`, sha256 }
    });
  }

  // The backgrounds channel (B90, `cachepal-backgrounds-v1`). Unlike the wardrobe file,
  // this one is NOT assembled here: the scene art is painted upstream in the CachePal
  // repo (`tools/background-file.mjs`, which inlines the PNG as base64 and validates
  // against the shipped C# rulebook's own limits), so the content repo stores the emitted
  // artifact VERBATIM and references it. Verbatim matters: the client checks the file's
  // SHA-256 against this payload, so re-canonicalising the bytes here would break the
  // very chain the reference exists to provide.
  //
  // `backgrounds/CURRENT` names the live file — one line, so a human can see at a glance
  // which artifact this generation ships, and a withdrawal is a one-line edit rather than
  // an archaeology exercise.
  const bgCurrent = join(ROOT, 'backgrounds', 'CURRENT');
  if (existsSync(bgCurrent)) {
    const name = readFileSync(bgCurrent, 'utf8').trim();
    if (!name) { console.error('backgrounds/CURRENT is empty — name the live file or delete the pointer.'); process.exit(1); }
    const bgPath = join(ROOT, 'backgrounds', name);
    if (!existsSync(bgPath)) { console.error(`backgrounds/CURRENT names ${name}, which does not exist.`); process.exit(1); }
    const bgBytes = readFileSync(bgPath);
    const content = JSON.parse(bgBytes.toString('utf8'));
    if (content.schema !== 'cachepal-backgrounds-v1' || !Array.isArray(content.backgrounds) || content.backgrounds.length === 0) {
      console.error(`backgrounds/${name} is not a non-empty cachepal-backgrounds-v1 file.`);
      process.exit(1);
    }
    channels.push({
      name: 'backgrounds', content, bytes: null, path: bgPath,
      ref: { file: `backgrounds/${name}`, sha256: createHash('sha256').update(bgBytes).digest('hex') }
    });
  }

  const payloadObj = {
    schema: 'cachepal-registry-v1',
    generation,
    publishedAt: new Date().toISOString(),
    species: entries
  };
  // Channel refs are additive, and omitted entirely when the channel ships nothing — an
  // absent field and a null one read the same to the client, but omitting it keeps the
  // payload honest about what this generation actually ships. `canonical` sorts keys, so
  // the signed bytes do not depend on the order they are attached in.
  for (const c of channels) payloadObj[c.name] = c.ref;

  // Gate 2 (B205): nothing that generation N published may be missing from N+1.
  assertAppendOnly(prev, payloadObj, all, channels);

  mkdirSync(join(ROOT, 'packs'), { recursive: true });
  for (const w of packWrites) writeFileSync(w.path, w.bytes);
  for (const c of channels) {
    if (!c.bytes) continue; // stored verbatim upstream — nothing to write
    mkdirSync(c.dir, { recursive: true });
    writeFileSync(c.path, c.bytes);
  }

  const payloadBytes = Buffer.from(canonical(payloadObj), 'utf8');
  const signature = sign(null, payloadBytes, privateKey);
  writeFileSync(join(ROOT, 'registry.pub.json'), JSON.stringify({
    payload: payloadBytes.toString('base64url'),
    signature: signature.toString('base64url')
  }, null, 2));

  const withdrawn = wardrobe.filter(c => c.delisted === true).length;
  const notes = channels.map(c => {
    const n = channelEntries(c.content, c.ref.file).keys.length;
    if (c.name === 'wardrobe') return `, wardrobe ${n} piece(s)${withdrawn > 0 ? ` (${withdrawn} withdrawn)` : ''}`;
    return `, ${c.name} ${n} entr${n === 1 ? 'y' : 'ies'}`;
  }).join('');
  console.log(`✔ published generation ${generation}: ${entries.length} species${notes}, signed.`);
}

/**
 * The previous signed payload — the thing append-only is measured against (B205).
 *
 * Refuses a baseline it cannot read INSTEAD of treating it as "nothing was published before,
 * therefore nothing can have been deleted". That inference is the vacuity that would make
 * every check below decorative: an empty, truncated or half-written registry.pub.json would
 * sail through a guard that only compares what it managed to load. A genuine first publish is
 * a real thing, so it gets a door — but a deliberate, named one you cannot walk through by
 * accident.
 */
function readBaseline() {
  const prior = join(ROOT, 'registry.pub.json');
  if (!existsSync(prior)) {
    if (process.env.PALPACK_ALLOW_GENESIS === '1') {
      console.log('  baseline: none, and PALPACK_ALLOW_GENESIS=1 says that is intended — publishing generation 1.');
      return null;
    }
    console.error('NO BASELINE: registry.pub.json is missing from this clone.');
    console.error('Publishing would sign generation 1 over a channel that is already serving a');
    console.error('later one, and no append-only check could run at all. Restore the clone.');
    console.error('If this really is the first publish ever: PALPACK_ALLOW_GENESIS=1');
    process.exit(1);
  }
  let prev;
  try {
    prev = JSON.parse(Buffer.from(JSON.parse(readFileSync(prior, 'utf8')).payload, 'base64url').toString('utf8'));
  } catch (e) {
    console.error(`UNREADABLE BASELINE: registry.pub.json did not decode — ${e.message}`);
    console.error('Refusing: a baseline that cannot be read cannot be appended to.');
    process.exit(1);
  }
  if (!Number.isInteger(prev.generation) || !Array.isArray(prev.species) || prev.species.length === 0) {
    console.error('EMPTY BASELINE: registry.pub.json decoded, but carries no generation number or no species.');
    console.error('Refusing: every comparison below would pass by having nothing to compare.');
    process.exit(1);
  }
  console.log(`  baseline: generation ${prev.generation}, ${prev.species.length} species, ${channelRefs(prev).size} channel(s).`);
  return prev;
}

/**
 * B205's actual incident, and the only check that can see it.
 *
 * `publish` re-signs the WHOLE registry from this clone, so the clone IS the next generation.
 * A clone that is behind does not merely miss new content: it silently unpublishes everything
 * added since it was last pulled, and the append-only guard cannot help, because a channel the
 * stale clone never knew about is absent from its baseline too. There is nothing to compare.
 *
 * So compare the baseline against the world: byte-for-byte with what the live channel is
 * serving at this moment. Equal generations with different bytes is the same failure wearing a
 * different hat — a re-sign that did not bump.
 *
 * Refuses rather than warns, because the incident it prevents produced no error anywhere and a
 * warning in a wall of publish output is not a stop.
 */
async function assertCloneIsCurrent(prev) {
  if (!prev) return; // genesis: already an explicit, named decision in readBaseline
  if (process.env.PALPACK_SKIP_FRESHNESS === '1') {
    console.warn('  freshness: SKIPPED by PALPACK_SKIP_FRESHNESS=1. You are asserting by hand that');
    console.warn(`  freshness: this clone is current. B205 is the incident that costs. (local generation ${prev.generation})`);
    return;
  }
  const url = process.env.PALPACK_REGISTRY_URL || `${LIVE_BASE}/registry.pub.json`;
  let liveText;
  try {
    const res = await fetch(url, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    liveText = await res.text();
  } catch (e) {
    console.error(`CANNOT CONFIRM FRESHNESS: ${url} — ${e.message}`);
    console.error('Refusing rather than warning: publishing from a clone of unknown age is how a');
    console.error('signed generation gets re-issued and a whole channel disappears with it (B205).');
    console.error('Offline on purpose? PALPACK_SKIP_FRESHNESS=1 — a decision, not a shortcut.');
    process.exit(1);
  }
  let live;
  try {
    live = JSON.parse(Buffer.from(JSON.parse(liveText).payload, 'base64url').toString('utf8'));
  } catch (e) {
    console.error(`CANNOT CONFIRM FRESHNESS: the live registry did not decode — ${e.message}`);
    process.exit(1);
  }
  if (!Number.isInteger(live.generation)) {
    console.error('CANNOT CONFIRM FRESHNESS: the live registry carries no generation number.');
    process.exit(1);
  }
  if (prev.generation < live.generation) {
    console.error(`STALE CLONE: this clone's baseline is generation ${prev.generation}; the live channel already serves ${live.generation}.`);
    console.error(`Publishing would re-issue generation ${prev.generation + 1} — already signed, already cached — and would`);
    console.error('drop every channel and entry the newer generations added, with no error anywhere.');
    console.error('Fast-forward the content clone (git pull) and start the drop again. This is B205.');
    process.exit(1);
  }
  if (prev.generation > live.generation) {
    console.error(`UNPUSHED PUBLISH: this clone's baseline is generation ${prev.generation}; the live channel serves ${live.generation}.`);
    console.error('A push IS the content deploy, so an unpushed publish is a generation the world never got.');
    console.error(`Push it before publishing again, or the next signature lands on ${prev.generation + 1} and ${live.generation + 1} is skipped forever.`);
    process.exit(1);
  }
  const localText = readFileSync(join(ROOT, 'registry.pub.json'), 'utf8');
  if (localText.trim() !== liveText.trim()) {
    console.error(`DIVERGED CLONE: this clone's registry.pub.json and the live one both say generation ${prev.generation}, but differ.`);
    console.error('One of them was signed without bumping, so "what the world has" is not what this clone');
    console.error('would append to. Reconcile before publishing — do not sign over it.');
    process.exit(1);
  }
  console.log(`  freshness: baseline generation ${prev.generation} is byte-identical to ${url}.`);
}

/**
 * Every payload key that holds a signed FILE channel, DERIVED from the payload itself (B205).
 *
 * A channel is any key whose value is a {file, sha256} ref — that shape is what makes the
 * client fetch, sha-verify and register a second file, so it is what makes a key a channel.
 * Nothing here knows the words "wardrobe" or "backgrounds", and that is the entire point: the
 * two-name list this replaced is why the backgrounds channel shipped unguarded, and a
 * three-name list would be why the fourth one does.
 */
function channelRefs(payload) {
  const out = new Map();
  for (const [k, v] of Object.entries(payload)) {
    if (v && typeof v === 'object' && !Array.isArray(v)
      && typeof v.file === 'string' && typeof v.sha256 === 'string') out.set(k, v);
  }
  return out;
}

/**
 * The entry list inside a channel file, derived the same way on both sides of the comparison.
 *
 * Channel files are `{ schema, <one array of entries> }` — `cosmetics` in
 * cachepal-cosmetics-v1, `backgrounds` in cachepal-backgrounds-v1 — so the entries are the
 * single array-valued property, not a property name this function was told. Anything it cannot
 * read that way is refused rather than skipped: "I could not find the entries" and "there are
 * no missing entries" must never produce the same outcome.
 */
function channelEntries(content, where, mustBeNonEmpty = false) {
  if (!content || typeof content !== 'object') {
    console.error(`CANNOT VERIFY ${where}: not a JSON object.`);
    process.exit(1);
  }
  const arrays = Object.entries(content).filter(([, v]) => Array.isArray(v));
  if (arrays.length !== 1) {
    console.error(`CANNOT VERIFY ${where}: expected exactly one array of entries, found ${arrays.length}`
      + `${arrays.length ? ` (${arrays.map(([k]) => k).join(', ')})` : ''}.`);
    console.error('Refusing: a channel whose entries cannot be located cannot be checked for deletions.');
    process.exit(1);
  }
  const [prop, list] = arrays[0];
  const keys = list.map(e => (e && typeof e.key === 'string') ? e.key : null);
  if (keys.some(k => !k)) {
    console.error(`CANNOT VERIFY ${where}: an entry in '${prop}' has no string 'key' to track it by.`);
    process.exit(1);
  }
  if (mustBeNonEmpty && keys.length === 0) {
    console.error(`CANNOT VERIFY ${where}: a previously published channel file with zero entries is not`);
    console.error('what was published. Refusing rather than passing a comparison against nothing.');
    process.exit(1);
  }
  return { prop, keys };
}

/**
 * Nothing generation N published may be missing from N+1 (B205, D30, D61).
 *
 * Three deletions, one shape: a species id, a whole channel, an entry inside a channel. The
 * channel set comes from `channelRefs(prev)` — the previous payload's own keys — so a channel
 * added in the future is guarded from its first published generation with no edit here, and a
 * channel this run simply forgot to emit is a refusal rather than a silent unpublish.
 *
 * Growth is explicitly fine. A channel that has never existed may appear, because a guard that
 * refuses growth is a guard the next person who needs to grow switches off.
 */
function assertAppendOnly(prev, next, allSpecies, channels) {
  if (!prev) return; // genesis, already opted into loudly
  const byName = new Map(channels.map(c => [c.name, c]));

  for (const p of prev.species) {
    if (!allSpecies.some(a => a.species.id === p.id)) {
      console.error(`APPEND-ONLY VIOLATION: id ${p.id} (${p.key}) vanished from species/. Delist it instead.`);
      process.exit(1);
    }
  }

  const before = channelRefs(prev);
  const after = channelRefs(next);
  let comparedChannels = 0;
  let comparedEntries = 0;

  for (const [name, ref] of before) {
    if (!after.has(name)) {
      console.error(`APPEND-ONLY VIOLATION: channel '${name}' is in generation ${prev.generation} and would not be in ${prev.generation + 1}.`);
      console.error(`Generation ${prev.generation} named ${ref.file}; this run names nothing, so publishing`);
      console.error(`would UNPUBLISH the whole channel for everyone who owns something in it — silently,`);
      console.error('because the client simply stops seeing a field it used to read.');
      console.error(`If this clone's palpack predates '${name}', it is the wrong clone to publish from (B205).`);
      process.exit(1);
    }
    const priorPath = join(ROOT, ref.file);
    if (!existsSync(priorPath)) {
      console.error(`CANNOT VERIFY channel '${name}': generation ${prev.generation} names ${ref.file}, which is not in this clone.`);
      console.error('Refusing: without the previous file there is nothing to compare, and passing here');
      console.error('would let every entry in the channel disappear unnoticed.');
      process.exit(1);
    }
    // The prior file must BE the artifact generation N signed, proven against the sha the
    // payload already pins — not merely a file sitting at that path. Found by attack: the
    // backgrounds artifact is stored verbatim under a stable name, so editing a scene OUT of it
    // in place left `prior` and `next` as the same bytes on disk and the entry comparison
    // passed against itself. A published channel file is immutable (the upstream painter emits
    // `backgrounds-<sha8>.json`, the wardrobe writer emits `cosmetics-<sha8>.json`), so a
    // mismatch here means the record of what was published no longer exists.
    const priorBytes = readFileSync(priorPath);
    const priorSha = createHash('sha256').update(priorBytes).digest('hex');
    if (priorSha !== ref.sha256) {
      console.error(`CANNOT VERIFY channel '${name}': ${ref.file} no longer hashes to what generation ${prev.generation} signed.`);
      console.error(`  signed  ${ref.sha256}`);
      console.error(`  on disk ${priorSha}`);
      console.error('A published channel file is immutable. Edited in place it can no longer say what was');
      console.error('published, and every deletion made inside it would pass by being compared to itself.');
      console.error('Emit a NEW content-hashed file and point the channel at that instead.');
      process.exit(1);
    }
    let priorContent;
    try { priorContent = JSON.parse(priorBytes.toString('utf8')); }
    catch (e) {
      console.error(`CANNOT VERIFY channel '${name}': ${ref.file} did not parse — ${e.message}`);
      process.exit(1);
    }
    const wasEntries = channelEntries(priorContent, `${ref.file} (generation ${prev.generation})`, true);
    const nowChannel = byName.get(name);
    if (!nowChannel) {
      // The ref survived into the payload but no descriptor built it: unreachable today, and a
      // refusal rather than a crash if a future edit makes it reachable.
      console.error(`CANNOT VERIFY channel '${name}': the payload names it but nothing assembled it.`);
      process.exit(1);
    }
    const nowEntries = channelEntries(nowChannel.content, nowChannel.ref.file);
    const missing = wasEntries.keys.filter(k => !nowEntries.keys.includes(k));
    if (missing.length > 0) {
      const hint = name === 'wardrobe'
        ? `  node tools/palpack.mjs withdraw ${missing[0]} "<reason>"`
        : `  keep the entry in the file — it is what an owner's copy resolves against.`;
      console.error(`APPEND-ONLY VIOLATION: ${name} entr${missing.length === 1 ? 'y' : 'ies'} ${missing.map(k => `'${k}'`).join(', ')} `
        + `vanished from ${nowChannel.ref.file}.`);
      console.error('Whoever owns one keeps the purchase and loses the thing: it stops resolving, so it');
      console.error('stops appearing, with no error on their device. Stop distributing; never confiscate.');
      console.error(hint);
      process.exit(1);
    }
    comparedChannels++;
    comparedEntries += wasEntries.keys.length;
    console.log(`  append-only: ${name} ${wasEntries.keys.length} → ${nowEntries.keys.length} entr${nowEntries.keys.length === 1 ? 'y' : 'ies'}, none removed.`);
  }

  for (const name of after.keys()) {
    if (!before.has(name)) console.log(`  append-only: '${name}' is a NEW channel — allowed, the guard is append-only, not frozen.`);
  }

  // The anchor. Everything above can only report a violation it FOUND, so say what was found;
  // a run that compared nothing while the baseline carried channels has not verified anything.
  if (before.size !== comparedChannels) {
    console.error(`GUARD INCOMPLETE: ${before.size} channel(s) in generation ${prev.generation}, ${comparedChannels} compared.`);
    process.exit(1);
  }
  console.log(`  append-only: compared ${prev.species.length} species and ${comparedChannels} channel(s)`
    + ` / ${comparedEntries} channel entr${comparedEntries === 1 ? 'y' : 'ies'} against generation ${prev.generation}.`);
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
