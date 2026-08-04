# Tallymite & Shinglecoat — HELD from drop 2026-W32

**This is not an art hold.** Both species are finished and both clear the geodecoil bar
(numbers below). They are held because `tools/palpack.mjs` will not validate the
`crawler` archetype, and deciding whether it should is an owner call about the oldest
client in the wild — not something a content lane may settle on its own.

The two sources are complete and sit beside this note as `HELD-tallymite.json` and
`HELD-shinglecoat.json`. Nothing about them needs redrawing or rewriting. When the
question below is answered they move with `git mv` into `species/` and nothing else.

## The blocker, precisely

`tools/palpack.mjs` line 76:

```js
const ARCHETYPES = new Set(['blob','quad','wisp','shell','fish','avian','biped','jelly','serpent']);
```

Nine. The game has **eleven** — `bloom` and `crawler` arrived with B25 and shipped in
**v1.25.0** (`STATUS.md`: *"Packs naming either now validate instead of hard-failing"*).
The content repo's validator still carries the pre-B25 nine.

Evidence, both directions, run in this worktree:

- With all four species staged in `species/`:
  `INVALID species/shinglecoat.json: bodyArchetype must be one of blob/quad/wisp/shell/fish/avian/biped/jelly/serpent`
- With **only** the archetype string swapped to `shell` and nothing else touched:
  `✔ all valid — 10 species, 3 wardrobe piece(s)`

So the archetype is the **sole** blocker. Ids, keys, colours, stat biases, need-decay
biases, feature grids, weights and all six prose fields already pass.

## Why a lane must not just add `crawler` to that set

It is one word, and that is exactly why it is worth stopping on.

The client rejects an unknown archetype by dropping the **whole pack**
(`ContentSyncService.TryRegisterPack`: `!PalSpriteGrids.HasArchetype(...)` → `return false`).
So on any build older than **v1.25.0**, a published `crawler` species does not degrade
to a default body — it becomes a **dormant mystery egg**, silently, for every player who
rolls it. That is generation 4's symptom arriving through a different door, and it is the
failure `docs/PACK_FORMAT.md` is organised around.

`PACK_FORMAT.md` already names the rule this falls under: *"The client build containing
that reader must be the floor: the oldest build still in use, not merely the newest
published… Authoring the field is free, publishing it is not."* Whether v1.25.0 is the
floor in the wild is a fact about real installs that this repo does not contain.

Two readings of the nine-item set are both live, and they point opposite ways:

1. **Stale.** palpack was simply never updated after B25, and the fix is one word.
2. **Deliberate.** The set encodes exactly the pre-B25 archetypes, i.e. it *is* the floor
   guard, and adding `crawler` removes a brake on purpose.

The line carries no comment either way, while `BUILTIN_MAX_ID` and `LIVE_BASE` directly
above it both carry their rationale — which leans toward (1) in a codebase this heavily
annotated, but leaning is not knowing.

**No harness catches this.** `deploy/checks/pack-agreement.mjs` only probes
`bodyArchetype: 'notarealarchetype'`; it asserts palpack refuses what the client refuses
and never asserts palpack *accepts* every archetype the client knows. palpack being
**stricter** than the client is the safe direction, so the divergence is invisible by
design. It passed green in this worktree while blocking both species.

## What the owner has to decide

> Is **v1.25.0** the floor build in the wild — i.e. may content ship `crawler` and
> `bloom` species now?

- **Yes** → add `crawler` and `bloom` to palpack's `ARCHETYPES`, `git mv` both files
  into `species/`, and consider a `pack-agreement` case that iterates
  `PalSpriteGrids.ArchetypeKeys` so the two sets can never drift again.
- **No** → both stay here until the floor moves. They cost nothing waiting.

Either way `bloom` has the identical problem and no species yet, so answering this once
settles both archetypes.

## The art, for the record (not the reason for the hold)

Measured with the same numbers the geodecoil note refused art on:

| | dark ink | body:outline | floating parts | edge cells | silhouette added (Teen/Adult) |
|---|---|---|---|---|---|
| Tallymite Teen/Adult | 40.8% / 37.5% | 1.45 / 1.78 | 0 | 0 | 2 / 1 |
| Shinglecoat Teen/Adult | 39.4% / 33.8% | 1.57 / 2.10 | 0 | 0 | 8 / 3 |

Geodecoil was refused at 52.7% dark ink and a 0.58 body-to-outline ratio, with welded
parts and stages that did not share a morphology. Both of these sit well clear on every
one of those axes, carry no free-floating parts, spend no cell on the frame edge (so the
keyline can ring them completely), and share one morphology across Teen and Adult by
construction — a pack supplies **one** overlay and `RegisterFeature` applies it to both
stages, so the stages cannot disagree.

Tallymite's silhouette addition is deliberately small: a single upright stylus is the
whole of its shape, because a neat instrument that adds one tidy thing is the point of
it. If a reviewer wants more shape on it, that is a taste call and worth making
explicitly rather than by drift.
