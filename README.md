# Cache Pal Content

Hot-loadable species and wardrobe content for [cachepal.com](https://cachepal.com),
served via GitHub Pages. A push to `main` **is** a content deploy — no app release
and no GitHub Actions minutes are consumed.

## Read this first if you are an agent

This repo holds content and the pipeline that signs it. It does **not** hold the
game. The authoritative documents live in the `the3dcoder/CachePal` repo and win
any disagreement with this file:

- `STATUS.md` — what is actually shipped. Never plan something listed there.
- `docs/PACK_FORMAT.md` — the binding pack contract (schemas, additive fields).
- `docs/runbooks/WEEKLY_DROP_RUNBOOK.md` — the end-to-end drop procedure.
- `docs/runbooks/TAKEDOWN.md` — how to delist content, and what cannot be undone.
- `docs/runbooks/CONTENT_KEY_ROTATION.md` — what the signing key protects.
- `DESIGN_DECISIONS.md` — D30 (registry as a frozen table), D37 (this host),
  D51 (Studio submissions), D52 (species living history), D53 (cosmetics ride
  v2 packs as an additive field).

## Layout

- `species/*.json` — source of truth, one file per species. Schema is
  `cachepal-pack-v1` for archetype-composed species, `cachepal-pack-v2` for
  species carrying their own 16×16 stage art.
- `packs/` — published, content-hashed, immutable packs (generated, committed). A
  superseded pack is kept, unless it holds a Pal's DNA (packs carried the first egg's
  DNA until 2026-10-11): `publish-drop.sh` removes those once the newly signed registry
  no longer names them. They stay in git history.
- `registry.pub.json` — signed envelope `{payload, signature}`; the payload is
  the canonical registry JSON (base64url), Ed25519-signed with the operator key.
- `DROPS.md` — the public drop log: what shipped when, plus each species'
  first-egg phrase. Never a DNA.
- `tools/palpack.mjs` — validate and sign: `new` / `validate` / `publish`.
- `tools/file-wave.py` — files a first-party species wave into the Barn queue as
  ordinary **pending** rows, so the operator approves it in `/admin` exactly like
  a community submission.
- `tools/build-drop.py` — turns the approved queue pool into species sources:
  assigns ids append-only, records each first-egg phrase, applies dex-edits and
  species-revisions oldest-first, and prints the close-loop commands.
- `tools/drop.py` — **the one command**: from the approved queue rows to a signed,
  pushed generation, its `DROPS.md` section and the stamped rows (below).
- `tools/dna-scan.py` — fails if any file this site serves holds a Pal's DNA.

## Rules (binding)

1. **Append-only ids.** Species ids are never reused, reordered, or removed —
   the registry is the frozen table behind DNA v2 decoding, and nothing may
   mutate what an already-issued DNA GUID decodes to. Takedown means setting
   `"delisted": true` and republishing: existing owners keep their Pals, new
   mints stop. Follow the takedown runbook rather than improvising.
2. Ids 0–13 are compiled into the app and never appear here. New species start
   at 14 and must fit u16 (≤ 65535).
3. **Custom stage art implies v2, in both directions.** A species carrying
   `gridBaby`/`gridTeen`/`gridAdult` must declare `cachepal-pack-v2` and must
   carry all three. A species without them stays v1, so clients predating v2
   parsing keep accepting it. The validator enforces both directions.
4. **New content capability arrives as an additive field on v2 — never a new
   schema string.** A new schema string makes older clients drop the entire pack.
   Fields added this way so far: `createdBy`, `history`, `premiereSeed`,
   `premiereDna` (retired 2026-10-11, see rule 11), `cosmetics`.
5. `statBias` totals ≤ 10 with each value in −5..8; `needDecayBias` in 0.6..1.3.
   That is the fairness envelope, and the validator is where it is enforced.
6. Every publish is signed. The private key exists in exactly one place — the
   operator's key file — and never in this repo, a workflow, or on a server.
7. The game verifies the registry signature **and** each pack's SHA-256 before
   caching anything. Never hand-edit a file under `packs/`; regenerate it.
8. `tools/palpack.mjs` is the authoritative validator for everything above. If
   this README and the validator disagree, the validator is right and this file
   is the bug.
9. **Every channel is append-only, not just species and cosmetics.** `publish`
   re-signs the WHOLE registry, so a channel this run does not emit is
   *unpublished* for everyone who owns something in it. The guard derives the
   channel set from the previous payload's own keys — anything shaped
   `{file, sha256}` — so a channel present in generation N and absent in N+1 is
   refused, and so is an entry inside one. Growth is fine: a channel that has
   never existed may appear. A published channel file is **immutable**; to change
   one, emit a new content-hashed file and repoint it, never edit it in place
   (`publish` checks the previous file against the sha the payload pins).
10. **Publish only from a clone that matches what the channel is serving.**
    `publish` fetches the live `registry.pub.json` and refuses unless this
    clone's is byte-identical. A stale clone re-issues a generation that is
    already signed and cached and silently drops whatever the newer generations
    added — which is what nearly happened in wave 40. `git pull` first.
11. **No DNA on a served page.** A DNA GUID is a clone code: anyone who holds one
    hatches the same Pal, and GitHub Pages serves every file here. A drop prints a
    species' first-egg phrase (`premiereSeed`), never its first egg's DNA; the game
    mints that egg from the phrase. `palpack validate` refuses `premiereDna`, and
    `tools/dna-scan.py` fails on any string the game would decode as a Pal's DNA, in
    any served file; `publish-drop.sh` runs it before signing and before pushing.

## Publish flow

One command, from this clone's root, once a person has approved rows in the Barn's
`/admin` (the Studio's queue is the only way in; approval is never the tool's):

```bash
python3 tools/drop.py --dry-run             # rehearse in a throwaway copy: writes nothing anywhere
python3 tools/drop.py --dry-run --fixture   # the same with a made-up version 2 row, any time
python3 tools/drop.py                       # publish: it rehearses again first, and stops if red
```

It checks the key's public half against the game's `ContentSyncService.PublicKeys[0]`,
reads the approved, unpublished rows through `az`, builds them, validates, scans for
DNA, signs and pushes through `publish-drop.sh` (which writes the drop into
`DROPS.md` in the same commit), stamps `PublishedAt` on exactly the rows it shipped
and prints what it published. With nothing approved and unpublished it publishes
nothing. Its checks: `python3 tools/test_drop.py`.

The steps it runs, by hand:

```bash
# 1. file a wave into the Barn queue as pending, then approve it in /admin
AZURE_STORAGE_CONNECTION_STRING='...' python3 tools/file-wave.py drafts/<wave>/*.json

# 2. assemble the approved pool into species sources. A version 2 row (the Studio
#    from 2026-10-11) carries its colours, shape, appetite and stage lines; only a
#    version 1 row needs a hand-written drafts/<wave>/<key>.overlay.json. Painted
#    overlays and second frames always go into the pack as drawn.
#    Its checks: python3 tools/test_build_drop.py (throwaway copies; touches nothing).
AZURE_STORAGE_CONNECTION_STRING='...' python3 tools/build-drop.py \
    --cachepal-root /path/to/CachePal [--overlays drafts/<wave>] --drop-tag YYYY-Www

# 3. validate, then sign, scan and push from a clean main (this deploys);
#    the count is the live species count plus the new ones
node tools/palpack.mjs validate
./tools/publish-drop.sh <count>

# 4. run the printed close-loop commands
```

For a one-off species with no queue row, `node tools/palpack.mjs new <key> <id>`
scaffolds a file to edit, then steps 3–4 apply.

GitHub Pages serves `main` at https://the3dcoder.github.io/CachePalContent/.
