# Lane C — batch 1, ids 28-31

Four species, two counterpart pairs. Authored, not published, not signed.

Two of the four are **blocked at `validate` by a tooling defect** and are not
shippable today; the other two are clean. See "Blocked" below.

---

## The idea both pairs are built on

The roster is meant to read as one world where two kinds of creature meet. So each
pair is one natural creature and one made one sharing a body plan, and the pairing
is carried by the art and the lore without either ever mentioning the other.

The device is the same in both pairs and is deliberately repeated: **the same anchor
on the body, grown against machined.**

| | natural | made |
|---|---|---|
| bloom, rows 9-11 around the stalk | Loamcap — a soft pale veil flaring off the cap | Parabloom — two hard accent struts bracing the mast |
| shell, rows 1-5 over the dome | Bramblewick — an irregular fringe, one sprig drooping over the front | Palisade — an even five-post rail with a lamp |

Same place, same silhouette family, opposite character. Nobody says "these two go
together" and the dex never explains it.

---

## The four

### 28 · Loamcap — bloom, natural

A fungus that came up under a hollow log and hears the ground. Its whole nature is
that it knows things and does not pass them on.

- `statBias [0, -2, 3, 5, 0, 4]` — Resilience 5 is its largest and is the loudest
  claim in its own description ("has not hurried since"). Signal 4 is the sense the
  description is actually about. Stealth 3 because it lives under a log. Mischief
  **-2**: it is the least prankish thing in the batch, and withholding is not
  mischief. Power 0, Luck 0 — a mushroom has neither.
- `needDecayBias [0.75, 0.85, 0.7, 1.25, 0.8]` — very low upkeep on everything
  except hygiene, which is high because it lives in leaf mulch. That follows from
  what it is rather than from wanting a gameplay hook.
- `hungryFor` windfall apples — a decomposer under a tree.

### 29 · Parabloom — bloom, made

A dish somebody left pointed at the sky. Hears everything and repeats all of it.

- `statBias [0, 3, -4, -1, 3, 7]` — Signal 7 is the roster's highest by some way and
  it is the entire creature. Stealth **-4** is the roster's lowest (latchback's -2
  was the previous floor): it is a dish on a mast that repeats things out loud, so
  it should be the easiest creature in the game to find. Mischief 3 for blurting,
  not malice — the description is explicit that it does not understand it is doing
  anything wrong. Luck 3 for what it catches by chance. Resilience -1: a thin mast.
- `needDecayBias [1.05, 1.2, 1.25, 0.8, 0.95]` — energy and happiness drain fastest
  (it turns all day and needs someone to talk at); hygiene slowest, because it is up
  in the wind and the rain washes it. The inverse of Loamcap on both, on purpose.
- `hungryFor` weather static.

### 30 · Bramblewick — shell, natural

Birds sat on it and a hedge grew. It walks the boundary its own hedge has become.

- `statBias [1, -1, 4, 4, 1, 0]` — Stealth 4 because a walking hedge is invisible in
  a hedgerow, which is its only real trick. Resilience 4 for thorns and years. Signal
  **0**: it neither seeks nor sends, which is exactly what Palisade is not.
- `needDecayBias [0.9, 0.8, 0.85, 1.15, 1.0]` — contented and slow; hygiene high
  because a hedge sheds.
- `hungryFor` nettle tops — what actually grows at the foot of a hedge.

### 31 · Palisade — shell, made

Set down to mark a boundary. The fence moved; nobody told it; it still walks the old
line exactly.

- `statBias [2, -3, -1, 5, 0, 4]` — Resilience 5 (it was built to stand) and Mischief
  **-3**, the batch's lowest, because it is on duty and has been for years. Stealth
  -1: a boundary marker's job is to be seen. Signal 4 — it measures constantly and
  knows precisely where it is, which is the sad part.
- `needDecayBias [1.0, 1.1, 0.9, 0.7, 1.1]` — hygiene 0.7 is the cleanest in the
  batch (sealed and machined, the opposite of Bramblewick) and happiness 1.1 because
  it needs the line confirmed.
- `hungryFor` fence nails.

Bramblewick and Palisade invert on exactly the two stats their descriptions differ
on — Stealth 4 / -1 and Signal 0 / 4 — and agree on Resilience, which is the one
thing both of them are.

---

## Art

One `feature` grid per species over the archetype body. Every grid was composited
onto the **real** bloom and shell Teen and Adult bodies before it was written down.

Three constraints drove nearly every decision, and none of them were guessable:

1. **A pack feature is registered for Teen AND Adult from one grid**
   (`PalSpriteGrids.RegisterFeature`), unlike a builtin, which authors a grid per
   stage. So the grid has to be correct on two different bodies at once.
2. **The two stages do not share a face position.** Bloom's eyes sit at row 5 cols
   4-5 / 9-10 on Teen and row 4 cols 5-6 / 10-11 on Adult; the face centre moves
   from col 7 to col 8. There is no row of the cap that is safe above both eyes.
   Shell keeps its face rows (9-11) but shifts one column left into Adult.
3. **Feature overlays never apply to Baby** — babies stay generic-cute by contract.

Consequence for the writing: every baby line describes the bare archetype, and the
part the overlay adds arrives in the **teen** line — which is also when it arrives on
screen. Loamcap's teen line is "the skirt has come down"; Parabloom's is "the horn
has gone up"; Palisade's is "the posts are up and the lamp is lit". The prose and the
renderer agree about when the creature changes.

Measured against the failure modes the geodecoil hold lists:

| | body:outline | dark ink | silhouette added | orphan cells | state cells lost |
|---|---|---|---|---|---|
| geodecoil (held) | 0.58 | 52.7% | — | — | damaged 4 overlays |
| Loamcap | 1.35 / 1.31 | 25.5% / 23.5% | 8 / 6 | none | none |
| Parabloom | 1.30 / 1.24 | 29.4% / 27.0% | 8 / 7 | none | none |
| Bramblewick | 1.14 / 1.64 | 29.5% / 23.7% | 12 / 5 | none | none |
| Palisade | 1.14 / 1.59 | 29.8% / 24.4% | 11 / 6 | none | none |

(Teen / Adult. "Orphan cells" is painted cells with no orthogonal neighbour in the
**composed** frame — the welded-or-floating fault. "State cells lost" is decoration
cells the five generic overlays can no longer paint because the feature filled a
background cell they needed; uppercase paints on background only.)

None of the four touches an eye, a mouth or a cheek in either stage.

**Honest read on each.** Loamcap and Bramblewick clear the bar comfortably: a cap
with a ring and a hanging veil reads as a mushroom, and an irregular fringe with a
sprig over the front reads as a hedge growing on a shell. Palisade clears it — an
even comb with a lit middle post reads as a fence, and it is unmistakably the same
object as Bramblewick built rather than grown. **Parabloom is the weakest of the
four and I want that on the record:** a three-cell horn on a one-cell strut plus two
mast struts is a *plausible* satellite dish but not an unambiguous one, and at 16px
it could also read as a flower with a bud. It has no faults — no orphans, no state
damage, correct on both stages — it is simply quiet. I chose not to add more ink
because the geodecoil failure was too much ink, not too little, and because the
alternatives I tried were worse (below).

---

## Rejected, and why

- **Cap warts on Loamcap** (accent flecks at row 3). Bloom's Teen and Adult eyes
  occupy different columns, so any wart row lands directly above one Adult eye and
  not the other — it read as a single raised eyebrow rather than a fungus wart.
  Cut; the veil carries the mushroom on its own.
- **A `C` berry in Bramblewick's hedge.** `C` is the cheek colour and is a fixed pink
  independent of the species (`Darken(#FF9EB5, 0.22)`), so a `C` cell far from the
  face renders as a stray blush floating in a bush — a rendering fault, not fruit.
  Replaced with an `S` highlight at the tip (new growth).
- **A tripod for Parabloom** (legs at row 1, cols 4 / 7 / 10). Fine on Teen, where
  row 1 is background; on Adult row 1 *is* the cap's crown outline, so the legs
  became three isolated accent cells punched into the rim and read as notches. Also
  cost a Sleep-B and a Dirty-A decoration cell. Replaced with a single centre strut,
  which roots into the crown as a mount instead.
- **Ribs across Parabloom's dish underside** (row 8). Would have said "machined"
  loudly, but row 8 sits directly under the face and the ribs flanked the mouth —
  they read as teeth. Cut, accepting the quieter silhouette described above.
- **A courier / parcel concept for the made shell.** Dropped because Latchback is
  already a box with a lid on `shell`, and two box-on-legs species in one archetype
  is a roster problem regardless of how the lore differs.
- **Moss or shell-rings for the natural shell.** Both belong to Mossbyte ("one ring
  per software update"), which is the other `shell` builtin.
- **`element`, `history`, `premiereSeed`, `premiereDna`.** All omitted. `history` and
  `premiereSeed` are player-visible dex fields, and there is no drop and no premiere
  specimen yet — writing "created (drop 2026-W32)" would assert a drop that has not
  happened. `element` is documented as a v2 additive field and these are v1 packs.

---

## Blocked: the bloom pair does not pass `validate`

```
$ node tools/palpack.mjs validate
INVALID species/loamcap.json: bodyArchetype must be one of
blob/quad/wisp/shell/fish/avian/biped/jelly/serpent
EXIT=1
```

`tools/palpack.mjs` knows **nine** archetypes. The game has had **eleven** since B25
added `bloom` and `crawler` (`PalSpriteGrids.Archetypes`, which `HasArchetype` reads
and `ContentSyncService.TryRegisterPack` calls). So the validator refuses an
archetype the shipped client renders.

Nothing caught it because the cross-repo harness only probes one direction:
`pack-agreement.mjs` proves palpack REJECTS everything the client rejects, since the
expensive failure is palpack *accepting* what the client drops. There is no probe for
the converse.

**The constant is deliberately not changed here.** Whether it is safe to widen
depends on the floor build actually installed in the wild, which this lane does not
know: an unknown archetype makes a client drop the **whole pack**, so a `bloom`
species reaching a pre-B25 client is a dormant mystery egg rather than a fallback
body. That is an owner decision, not a lane's.

The shell pair validates clean on its own:

```
$ node tools/palpack.mjs validate     # bloom pair removed, throwaway copy
✔ all valid — 8 species, 3 wardrobe piece(s)
EXIT=0
```

---

## Validators run

| tool | verdict |
|---|---|
| `palpack.mjs validate` (this repo) | **shell pair PASS** — 8 species, 3 wardrobe, exit 0. **bloom pair BLOCKED** — output above, exit 1. |
| `deploy/checks/pack-agreement.mjs` | **PASS**, 12/12 OK, worktree restored clean. Its control accepted `bramblewick.json` as a well-formed donor pack. |
| `deploy/checks/publish-guard.mjs` | **PASS** on a pristine clone and on a clone with Palisade added: 24/24, `✔ PUBLISH GUARD OK`. One probe (A14) fails when Bramblewick is present — that is the probe, not the guard; see below. |
| `tools/sprite-validate.mjs` | **DOES NOT APPLY** — see below. |
| `tools/shape-sheet.mjs` | **DOES NOT APPLY** — see below. |
| `tools/sprite-draft.mjs` | **DOES NOT APPLY** — takes a reference PNG and emits a first-draft *body* grid. No reference art, and the wrong artefact. |
| `tools/drop-sheet.mjs` | **DOES NOT APPLY** — answers "does this wardrobe piece read on this Pal". Cosmetics, not species features. |

### `sprite-validate.mjs` does not cover a v1 feature overlay

It derives its rules from `SpeciesSubmission` — the **body-grid** rulebook: ≥24
painted, ≥8 `B`, ≥4 `O`, alphabet `.ABCEMOSWX`. A v1 `feature` is a different
artefact on a different legend (`.OBSAEWMC#` — `#` erases, no `X`), is sparse by
construction, and contains no body, no outline and no eye, because all three come
from the archetype underneath.

Proof rather than argument — the **shipped Prismite overlay**, first-party art on
the same archetype, fails it identically:

```
$ node tools/sprite-validate.mjs prismite16.grid
✘ 3 error(s)
    11 painted cell(s), the floor is 24.
    0 body (B) cell(s), the floor is 8.
    0 outline (O) cell(s), the floor is 4.
  ⚠ no eye (E) anywhere.
  ⚠ 11 isolated painted cell(s) with no orthogonal neighbour
```

The isolation warning is the clearest tell: an overlay's cells are *supposed* to
float, because the body they sit on is not in the file. That is why the orphan check
in the table above is measured on the **composed** frame instead.

### `shape-sheet.mjs` does not cover a pack species

`BarnCheck`'s `DumpSheetFrames` builds **scratch species with no feature overlay**,
explicitly "so the ARCHETYPE grid is what gets drawn", plus whichever species a wave
re-bodied. It is the review instrument for an archetype silhouette change. There is
no path for a content-repo pack's `feature` to reach it without publishing and
syncing first, which is out of scope here. (`dotnet` 10.0.110 is present, so this is
a coverage conclusion, not a missing-toolchain one.)

### A14 in `publish-guard.mjs` is fragile, and a lane will trip it

A14 deletes `readdirSync('species')[0]` — the alphabetically **first** file — and
asserts publish refuses it as an append-only violation. That assumes the first file
is a *published* species. `bramblewick` sorts before `emberimp`, the earliest
published key, so the probe deletes a brand-new unpublished species, publish
correctly succeeds, and the check reports a failure that is not one.

Isolated three ways:

- pristine clone (6 species) → `✔ PUBLISH GUARD OK`
- clone + Palisade only (sorts after `emberimp`) → `✔ PUBLISH GUARD OK`
- clone + Bramblewick → A14 alone fails, `exit 0 :: ✔ published generation 10`

The guard itself is intact — every refusal still refuses. The probe needs to pick a
victim that appears in the previous signed payload rather than whatever sorts first.
**Any lane whose species key begins a–e will hit this**, so it is worth fixing before
the batch is integrated rather than being re-diagnosed three times.

---

## For the owner

- **Earned-unlock candidate: Palisade (31).** Nominated in the report; the short
  version is that it is the only one of the four whose lore is *about* having been
  put somewhere by someone, so arriving later reads as intended rather than as
  withheld. It also has the batch's lowest spawn weight (38) already.
- The `bloom` archetype question above is a genuine owner call and is the thing
  blocking half this lane.
