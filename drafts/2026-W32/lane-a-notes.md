# Wave 47, lane A — four species, two counterpart pairs

Ids 20–23. Authored sources only: **nothing here is published and nothing is signed.**
Lanes B and C hold 24–27 and 28–31.

| id | key | archetype | pair | side |
|---|---|---|---|---|
| 20 | `pilotwire` | serpent | 1 | digital |
| 21 | `wickroot` | serpent | 1 | natural |
| 22 | `blinkbell` | jelly | 2 | digital |
| 23 | `eavesdrop` | jelly | 2 | natural |

Both archetypes had exactly one species across the whole roster before this
(`snagglet`, `driftjelly`). This takes each to three and leaves quad on four.

---

## The world rule these four are built on

The brief asked for pairs that read as counterparts without ever saying so. Rather than
pair them by *subject*, they are paired by **rhythm**, in the same two slots on the same
body:

- **rows 0–2 — how it presents itself at the leading end.** Digital: a made fitting,
  symmetrical, with its own outline. Natural: a grown tip, asymmetrical, merging into the
  body with no outline at all.
- **one row further down its length — the marks along it.** Digital: identical marks at
  even spacing. Natural: marks of different sizes at uneven spacing.

Both pairs obey it, so the four read as one world rather than two sets. Colour carries
the same rule quietly: the two digital species are saturated, the two natural ones muted.

A side effect worth keeping: because each species' identity is split across two zones and
the cosmetic slots band differently (hat crown rows 0–4, scarf rows 8–11 before the
per-archetype offset), **no single cosmetic slot can erase a whole species tell.** A hat
hides the crown and leaves the rhythm; a scarf hides the rhythm and leaves the crown.

---

## 20 · Pilotwire — serpent, digital

The draw-line someone pushes under a road so a cable can follow it. It goes first, in the
dark, alone, and the thing everyone actually wanted comes after.

Life story: cannot turn a corner → crosses a room under the carpet → crosses under a
road. One animal, three ages.

**statBias `[1, -1, 2, 2, 0, 4]` (total 8, house norm).**
`Signal 4` is the peak because the creature exists so that a connection is made — that is
the whole of it. `Mischief -1` is the character stated as a number: it does not deviate,
ever; a positive Mischief would contradict the first line of its own description.
`Stealth 2` — it works under roads, unseen. `Resilience 2` — tough, but it is a thin line,
not Ferrite. `Power 1` — it pushes, weakly. `Luck 0` — nothing about it is luck.

**needDecayBias `[0.8, 0.9, 1.25, 1.15, 1.0]`** — Energy highest (it works a long shift in
a duct), Hygiene next (it comes back through forty metres of grit), Hunger low (it is a
wire).

**hungryFor `duct grease`** — the pulling lubricant it spends its life in.

**Art (9 cells).** A short upright post on the brow, `O A O` shoulders with a `W` bead on
top: a lamp, symmetrical, bolted on, with its own outline. Along the back, two identical
two-cell bands at columns 6 and 10 — even, repeating, machined. The adult line "with a
lamp on its head" was rewritten to match the art after the art changed; an earlier draft
said "with a loop on the end" and the loop had already been rejected (below).

## 21 · Wickroot — serpent, natural

A root that hunts damp. It does not choose where it goes; the damp chooses and it agrees
enthusiastically. Crosses car parks, lifts flagstones, arrives in cellars.

Life story: a pale thread leaning toward the wet side of a stone → has crossed the path
and cannot be pulled up → old, brown, knuckled, mended in a hundred places.

**statBias `[3, 3, 2, 2, 0, -2]` (total 8).**
`Power 3` is earned by the description, not decoration — it lifts two flagstones, which is
real force applied slowly. `Mischief 3` is "comes up through the floor". `Signal -2` is
the exact inverse of Pilotwire's `+4`: nothing can reach it and it has no interest in
being reached.

The two serpents deliberately share `Stealth 2`, `Resilience 2`, `Luck 0` — both are long
things that travel under roads, and neither is lucky — and trade only Mischief and Signal.
The counterpart reading is in the numbers as well as the art, and nowhere in the prose.

**needDecayBias `[1.25, 0.8, 0.75, 1.3, 0.7]`** — Hygiene at the ceiling (it lives in
soil), Hunger high (it is growing), Energy and Intelligence low (it does not think, it
just goes toward wet).

**hungryFor `seep water`.**

**Art (9 cells).** An uneven two-pronged growing tip: a long prong at column 4, a short one
at column 6, joined by a three-cell base that replaces the head's crown outline with pale
highlight — the fork grows *out of* it rather than being fitted *to* it, which is the whole
contrast with Pilotwire's outlined post. Along the back, swellings at columns 6, 9 and 10:
one alone, then a pair. Uneven in both spacing and size.

## 22 · Blinkbell — jelly, digital

The small light on an empty ceiling that has watched a room where nothing has happened for
nine years, and is proud of every one of them. Once, at three in the morning, it was
certain something was happening. It was wrong, it was extremely serious about it, and it
apologised to the whole house.

Life story: nothing to watch yet, watching it closely → has learned the room and counts the
creaking board every night → nine years, still awake, still certain it will be needed.

**statBias `[0, 0, -2, 5, 0, 5]` (total 8).**
`Resilience 5` because endurance *is* the creature — nine years on the same ceiling.
`Signal 5`, the roster's highest, because its entire existence is telling you something.
`Stealth -2` because it is the least stealthy thing that has ever been made; it announces.
Three zeros: it has no power, no guile and no luck, and pretending otherwise would be the
kind of line the owner objects to.

**needDecayBias `[0.7, 0.85, 0.65, 1.1, 1.15]`** — Energy lowest (it sips), Intelligence
highest (it watches all night and learns the room), Hygiene high (nobody has ever cleaned
a ceiling).

**hungryFor `night current`.**

**Art (8 cells).** A rigid centred stalk on the crown with an `O A O` housing and a `W`
light on top, at **column 7 — a middle column on all three stages**, so no life stage skews
it by a pixel. Along row 8, three identical accent pips at columns 3, 6 and 9: even, three
apart, repeating.

## 23 · Eavesdrop — jelly, natural

The drop that hangs off every gutter for about an hour after rain, holding the whole road
upside down and getting slowly heavier. Nobody has ever looked up in time. It lets go at
roughly the moment you walk underneath, which it does not consider funny, and which is.

Life story: a bead too small to fall with the entire hedge already inside it → heavy enough
to wobble → a full drop at the end of its hour.

**statBias `[-1, 2, 4, -1, 1, 3]` (total 8).**
`Stealth 4` is earned: they are on every gutter on the street and you have never once
noticed one. `Resilience -1` and `Power -1` because it is a drop of water that lasts an
hour. `Mischief 2` is letting go over your collar — a smaller mischief than Wickroot's 3,
because it is not trying. `Signal 3`, because it holds and returns everything around it.

Against Blinkbell this is an exact inversion on the two axes that matter: `Resilience 5 /
Stealth -2` (lasts forever, cannot be ignored) against `Resilience -1 / Stealth 4` (lasts
an hour, is never noticed). Both keep Signal high, because both are the house's sense
organ. Neither description mentions the other.

**needDecayBias `[1.2, 0.7, 1.2, 0.6, 0.9]`** — Hygiene at the floor (it is rain; rain is
what cleans things), Hunger and Energy high (it drinks constantly and it evaporates).

**hungryFor `roof rain`.**

**Art (9 cells).** A one-cell thread at column 7 running down into a three-cell neck that
replaces the bell's crown outline with highlight — water has no line where it is
continuous, which is the opposite of Blinkbell's outlined housing in the same place. A
single `W` caustic on the dome. Along row 8, the same slot Blinkbell uses: one bead at
column 3, then a fat pair at 8 and 9. Uneven against Blinkbell's even.

---

## Things rejected on the way

- **A closed eyelet ring for Pilotwire's crown.** A 3×3 ring with a one-cell hole, meant to
  read as the eye you tie the cable to. It does not survive composition: the keyline is
  measured off the silhouette and painted into *any* remaining background cell, so the hole
  fills with keyline and the ring renders as a solid bead with a pale centre — an eye, not
  a loop. Replaced by the post-and-lamp, and the adult line rewritten to match rather than
  leaving prose describing art that is not there.
- **Eavesdrop's beading as `S`.** Drawn first as highlight, which worked on the Teen and
  disappeared completely on the Adult: the jelly Adult already carries `S` at row 8,
  columns 4–8, so two of the three beads landed on their own colour. Moved to `A`, which
  puts it in the same material as Blinkbell's pips and makes the even/uneven contrast a
  strict comparison on one row.
- **A ceiling mounting plate above Blinkbell.** A stem with a flat plate at row 0. Dropped:
  it is architecture, not creature, which is the first thing `HELD-geodecoil.md` refuses a
  species for. The "it is fixed up there" idea now lives entirely in the lore.
- **Wickroot's shoulder knuckle at (8,10).** A bump on the coil's shoulder. Legal and
  frame-safe, but on the Teen the body outline notches away at (8,9) so the bump sits one
  keyline cell clear of the body and reads as a detached nodule. Removed rather than
  shipped as "nearly attached".
- **Pilotwire's back marks as single cells two apart.** At 16×16 a one-cell mark repeated
  every two columns is a 50 % checkerboard and reads as dither, not as measurement. Widened
  to two-cell-tall bands four columns apart.
- **`element`, `premiereSeed`, `history` fields.** Deliberately omitted. `PACK_FORMAT.md`
  §2 is explicit that additive fields ride on **v2**; these are v1 packs, so they carry the
  required set and nothing else. For whoever files these into the Barn queue, the intended
  values are: Pilotwire — element *Wire*, seed "somebody has to go first"; Wickroot —
  element *Root*, seed "the damp decides"; Blinkbell — element *Watch*, seed "nine quiet
  years"; Eavesdrop — element *Rain*, seed "an hour after".

## Why v1 and not v2

None of the four carries `gridBaby`/`gridTeen`/`gridAdult`, so the pairing rule
(`PACK_FORMAT.md` §1, enforced both directions by `palpack.mjs`) requires `cachepal-pack-v1`.
That is also the better outcome here: v1 keeps them visible to clients that predate v2
parsing, and the whole point of this batch is a deeper roster on day one.

## Evidence

Every number below is reproducible; the local review harness that produced the composition
figures is scratch, not committed.

- `node tools/palpack.mjs validate` → **`✔ all valid — 10 species, 3 wardrobe piece(s)`**, exit 0.
- `CONTENT_REPO=$PWD node deploy/checks/pack-agreement.mjs` (game repo) → **12/12 OK**, exit 0.
- `CONTENT_REPO=$PWD node deploy/checks/publish-guard.mjs` (game repo) → **24 of 25 OK**;
  `A14` fails, and it is the harness's fixture rather than a refusal that moved. See below.
- `node tools/sprite-validate.mjs` on the 24 composed frames (4 species × Teen/Adult/Elder ×
  frames A/B) → **`OK — 24 input(s), every shipped rule met`**, exit 0, and **zero warnings
  that the bare archetype frame does not already emit**.
- Composition safety, measured per species across Teen, Adult and Elder on both frames:
  W150's overlay invariant (frame B agrees with frame A about background on every cell the
  overlay writes) holds everywhere; silhouette added +2…+6 cells, so none of the four is
  the bare archetype; body:outline 0.92–1.76 against a bare-archetype range of 1.06–1.69;
  dark ink 27.6–41.3 % against a bare-archetype range of 30.4–41.4 %. `HELD-geodecoil.md`
  was refused at 0.58 and 52.7 %.
- State-overlay decoration cells lost (a feature cell claiming a background cell an
  uppercase state decoration would have painted): Pilotwire 2 across 1 state, Wickroot 1
  across 1, Blinkbell 0, Eavesdrop 0. The shipped `snagglet` overlay loses 6 across 2;
  geodecoil was refused for damaging 4 at once.

### The `publish-guard` A14 failure

`A14` deletes `readdirSync('species')[0]` and asserts publish refuses. That fixture assumes
the first file on disk is a *published* species. With this branch applied the first file is
`blinkbell.json` — id 22, never published — so deleting it is a legitimate operation,
publish proceeds, and the attack walks through. Isolated three ways:

1. with the four new files moved aside, the guard is **25/25 green including A14**;
2. with only `pilotwire` and `wickroot` present (both sort after `emberimp`),
   `readdir[0] = emberimp.json` and the guard is again **25/25 green including A14**;
3. the run's own output shows the append-only clause working correctly throughout —
   "compared 6 species … published generation 10: 9 species".

So `palpack`'s refusal is intact and the harness's fixture selection is what changed. This
is latent in the game repo (`deploy/checks/publish-guard.mjs`, the `A14` block) and will
red for **any** future drop that adds a species key sorting before `emberimp` — the sibling
lanes on 24–31 will hit it too. Not fixed here: the fix belongs in the game repo and this
lane must not write to it.

### Tools that turned out not to apply

- **`tools/sprite-validate.mjs` on a raw `feature` overlay — does not apply.** It derives its
  rules from `SpeciesSubmission` (authorable alphabet `.ABCEMOSWX`, ≥24 painted, ≥8 `B`,
  ≥4 `O`), which are floors for a whole *body* grid. A v1 feature overlay is a different
  artefact in a different legend — `palpack`'s `LEGEND` is `. O B S A E W M C #`, and `#`
  (erase) is legal there and illegal in the role alphabet. Run against `pilotwire`'s overlay
  it reports three errors and one warning, all of them category errors. It is used above only
  where it genuinely applies: the *composed* frames, which really are role grids.
- **`tools/shape-sheet.mjs` — does not apply.** It is a before/after review sheet for an
  archetype **silhouette redraw** (its subject is `W95-STOOP`), it needs a dump from
  `SHAPE_SHEET_DUMP=… dotnet run --project tools/BarnCheck`, and it reads the compiled
  catalog — it has no path to an unpublished content-repo pack. No archetype silhouette
  moved here. Its `--self-test` was run anyway (4/4 OK, exit 0, wrote nothing to the game
  repo) so that "not applicable" is not covering for a broken instrument.
- **`tools/drop-sheet.mjs` — does not apply.** It answers "does this wardrobe piece read on
  this Pal". This lane authored no cosmetics.
- **`tools/BarnCheck` palette sweeps (`RosterPaletteChecks`, `ReachableSpaceChecks`) — not
  run.** These are the checks that would answer "is `#8FC3B6` far enough from the roster,
  and does it stay distinguishable from the Sick tint across the whole hue gene space" —
  the question B171 and the Mossbyte note were written about. They measure the **compiled**
  roster and cannot see a content pack, and running them means `dotnet run` inside the game
  repo, which writes build output into a tree this lane must not touch. **So the four base
  colours are reasoned, not measured**, and that is a real gap: they were chosen in bands
  the roster visibly leaves open (saturated indigo, root brown, deep rose, muted
  eucalyptus), all far in hue from the Sick blend target `#7FAE6A`, with `#8FC3B6` the
  closest at roughly 60°. Worth a sweep on the game-repo side before any of this is signed.

## For the operator

- **Weights** are 52 / 58 / 44 / 38, all non-zero, so all four are obtainable from day one.
- **Earned-unlock nomination: `eavesdrop` (23).** It is the only one of the four whose
  identity is scarcity — it exists for about an hour after rain — so gating it behind the
  expedition ladder would agree with its own lore instead of fighting it, and its low weight
  already points that way. No gating is attempted here; the ladder does not exist yet.
  **One cost, flagged rather than decided:** gating either half of a pair hides the pairing
  from every player who has not earned it. A new keeper would meet Blinkbell with nothing to
  read it against. Blinkbell stands alone as a character, so the damage is to the *set*
  rather than to the species — but whether the roster's legibility is worth more than the
  chase is a taste call, and it is the owner's.

## Open question for the owner (a taste call, not a technical one)

Blinkbell's lore is the only one of the four that is funny at the creature's expense — it
was wrong at three in the morning and apologised to the house. It is meant to be affection
rather than a joke, in the register the Lamplighter sets, but it is the one line here that
could read as a gag about a smoke alarm rather than a portrait of somebody. If it lands
wrong it is one sentence to cut, and the species survives the cut. Flagging rather than
guessing.
