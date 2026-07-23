# Cache Pal Content

Hot-loadable species content for [cachepal.com](https://cachepal.com), served
via GitHub Pages (D30/D37 in the CachePal repo's DESIGN_DECISIONS.md).

- `species/*.json` — source of truth, one file per species (`cachepal-pack-v1`)
- `packs/` — published content-hashed immutable packs (generated, committed)
- `registry.pub.json` — signed envelope `{payload, signature}`; the payload is
  the canonical registry JSON (base64url), signed Ed25519 with the operator key
- `tools/palpack.mjs` — the pipeline: `new` / `validate` / `publish`

## Rules (binding)

1. **Append-only ids.** Species ids are never reused, reordered, or removed —
   the registry is the frozen table behind DNA v2 decoding. Takedown = set
   `"delisted": true` and republish (owners keep their Pals; new mints stop).
2. Ids 0–13 are compiled into the app and never appear here. New species start
   at 14 and must fit u16 (≤ 65535).
3. `statBias` total ≤ 10 and each in −5..8; `needDecayBias` in 0.6..1.3 — the
   fairness envelope the validator enforces.
4. Every publish is signed. The private key exists in exactly one place (Earl's
   key file). `PALPACK_KEY=<PRIVATE value> node tools/palpack.mjs publish`.
5. The app verifies the signature AND per-pack SHA-256 before caching anything.

## Publish flow

```bash
node tools/palpack.mjs new <key> <id>   # scaffold species/<key>.json, then edit
node tools/palpack.mjs validate
PALPACK_KEY=... node tools/palpack.mjs publish
git add -A && git commit -m "content: <what>" && git push
```

GitHub Pages serves `main` at https://the3dcoder.github.io/cachepalcontent/ —
a push IS a content deploy. No GitHub Actions minutes are consumed (public repo).
