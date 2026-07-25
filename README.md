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
- `packs/` — published, content-hashed, immutable packs (generated, committed).
- `registry.pub.json` — signed envelope `{payload, signature}`; the payload is
  the canonical registry JSON (base64url), Ed25519-signed with the operator key.
- `DROPS.md` — the public drop log: what shipped when, plus each species'
  premiere code.
- `tools/palpack.mjs` — validate and sign: `new` / `validate` / `publish`.
- `tools/file-wave.py` — files a first-party species wave into the Barn queue as
  ordinary **pending** rows, so the operator approves it in `/admin` exactly like
  a community submission.
- `tools/build-drop.py` — turns the approved queue pool into species sources:
  assigns ids append-only, mints premiere DNA, applies dex-edits and
  species-revisions oldest-first, and prints the close-loop commands.

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
   `premiereDna`, `cosmetics`.
5. `statBias` totals ≤ 10 with each value in −5..8; `needDecayBias` in 0.6..1.3.
   That is the fairness envelope, and the validator is where it is enforced.
6. Every publish is signed. The private key exists in exactly one place — the
   operator's key file — and never in this repo, a workflow, or on a server.
7. The game verifies the registry signature **and** each pack's SHA-256 before
   caching anything. Never hand-edit a file under `packs/`; regenerate it.
8. `tools/palpack.mjs` is the authoritative validator for everything above. If
   this README and the validator disagree, the validator is right and this file
   is the bug.

## Publish flow

The normal weekly path is queue-driven, so every species — first-party or
community — gets approved in one place:

```bash
# 1. file a wave into the Barn queue as pending, then approve it in /admin
AZURE_STORAGE_CONNECTION_STRING='...' python3 tools/file-wave.py drafts/<wave>/*.json

# 2. assemble the approved pool into species sources
AZURE_STORAGE_CONNECTION_STRING='...' python3 tools/build-drop.py \
    --cachepal-root /path/to/CachePal --overlays drafts/<wave> --drop-tag YYYY-Www

# 3. validate, sign, publish
node tools/palpack.mjs validate
PALPACK_KEY=<PRIVATE value> node tools/palpack.mjs publish

# 4. commit and push (this deploys), then run the printed close-loop commands
git add -A && git commit -m "content: <what>" && git push
```

For a one-off species with no queue row, `node tools/palpack.mjs new <key> <id>`
scaffolds a file to edit, then steps 3–4 apply.

GitHub Pages serves `main` at https://the3dcoder.github.io/CachePalContent/.
