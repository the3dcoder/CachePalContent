# Wave 47, lane B — working notes

Four species, two counterpart pairs, ids 24–27. Sibling lanes hold 20–23 and 28–31.

| id | key | archetype | nature | state |
|---|---|---|---|---|
| 24 | `sendling` | fish | digital | in `species/`, validates |
| 25 | `riffleback` | fish | natural | in `species/`, validates |
| 26 | `tallymite` | crawler | digital | **held** — see `HELD-crawler-pair.md` |
| 27 | `shinglecoat` | crawler | natural | **held** — see `HELD-crawler-pair.md` |

The hold is a **tooling** hold, not an art or writing hold. `palpack.mjs` carries nine
archetypes and the game has eleven; `crawler` is not in the validator's set. Both crawler
sources are finished. Full reasoning, evidence and the owner question are in
`HELD-crawler-pair.md`.

## The world the four share

The owner's direction was one world where two kinds of creature meet, with each pair a
digital and a natural creature that are recognisably counterparts — same body plan, same
silhouette family, opposite natures, and never stated outright.

The two pairs are built on **different oppositions** on purpose, so the batch does not
read as the same joke twice:

- **The fish pair is about motion** — one is carried, one holds.
- **The crawler pair is about collecting** — one catalogues and keeps nothing, one keeps
  everything and catalogues nothing.

Both oppositions are about place and memory, which is the game's own subject, so they sit
in one world without either pair repeating the other.

The two naturals are both riverine (a stone in fast water; the shingle of the same
stream) and the two digitals both live in the moving parts of a machine. That was not
required, but it makes the batch read as one place rather than four ideas.

### Pair 1 — `fish`: Sendling (digital) / Riffleback (natural)

Same fish body. **Sendling** rides whatever is moving and has never been anywhere long
enough to know it. **Riffleback** picked one stone and has not left it. One has crossed
enormous distance and retained nothing; the other has held four feet of riverbed for
years and knows every pebble of it. Neither line mentions the other.

Read from the art: Sendling is bright synthetic cyan with **horizontal** pale streaks
(the flow going past, and the light on a body in motion) and a **raised pointed** dorsal —
its mass is high, up in the current. Riffleback is drab olive with **vertical** pale bars
(a banded, stone-coloured fish that vanishes against gravel) and a **low blunt** profile
with a broadened ventral paddle — its mass is low, braced on the bottom. Horizontal
versus vertical, bright versus drab, high versus low, on one body.

### Pair 2 — `crawler`: Tallymite (digital) / Shinglecoat (natural)

Same plated crawler. **Tallymite** walks every surface once, in order, and marks off
what it has covered; it keeps nothing and records everything. **Shinglecoat** cements one
found object at a time to its back, keeps everything, and could not tell you where any of
it came from. The final two sentences of Tallymite's description and the middle of
Shinglecoat's are the hinge, and neither names the other.

Read from the art: Tallymite has a **single upright stylus** and **three evenly spaced**
pale ticks along its carapace. Shinglecoat has an **irregular lumpy crown** and
**randomly scattered** grains stuck over its back. Order versus accumulation, on one
dome. This is the pairing that reads best of the two.

Shinglecoat's encrustation is authored in the `A` (accent) role deliberately: accent is
chosen by DNA gene G6 rather than by the species, so the grit comes out a colour the
creature did not pick — which is exactly right for a coat made of other people's things.

## Why the stat lines say what the descriptions say

`statBias` is `[Power, Mischief, Stealth, Resilience, Luck, Signal]`, ints −5..8, and the
fairness cap is the **sum** ≤ 10. Roster sums today run 7–9; nothing here exceeds 8.

**Sendling `[-1, 3, -2, -2, 4, 4]` = 6.** Small and carried rather than strong (−1). A
stowaway on other people's traffic (+3). It cannot hide, because holding still is what
hiding needs and it cannot do that (−2) — the direct inverse of Riffleback. No staying
power; it moves on (−2). Its whole life is where the flow happens to put it (+4 Luck),
and it is, functionally, a transmission (+4 Signal).

**Riffleback `[3, -3, 4, 4, 0, -1]` = 7.** Holding station in fast water is real
muscular work, all day (+3 Power). The least mischievous thing on the roster — it does
one thing (−3), which is the trap the brief warned about and the reason this number is
negative rather than decorative. Motionless and stone-coloured against gravel (+4
Stealth). Endurance is its entire character (+4 Resilience). It does not gamble, it
stays (0 Luck). It is the quiet one (−1 Signal).

**Tallymite `[0, -3, -1, 5, -2, 5]` = 4.** Lifts nothing (0). Utterly methodical;
mischief is deviation from the route and it does not deviate (−3). It cannot hide because
it writes down everywhere it has been (−1). It finishes the sweep, always (+5). It leaves
nothing to chance, by design (−2). Its entire output is a catalogue (+5).

**Shinglecoat `[2, 1, 2, 4, 2, -3]` = 8.** Carries its whole collection on its back
(+2). Will quietly take a button off your coat (+1 — mild, not playful). Looks exactly
like a heap of grit (+2 Stealth). Armoured and slow (+4). A creature whose life is
finding small objects (+2 Luck). Keeps everything and tells nobody (−3 Signal).

The two crawlers deliberately **share** high Resilience (+5 / +4). They have the same
body plan, so the physical class should match; the opposition belongs in temperament,
which is where every other axis inverts (Mischief −3/+1, Stealth −1/+2, Luck −2/+2,
Signal +5/−3).

`needDecayBias` is `[Hunger, Happiness, Energy, Hygiene, Intelligence]`, 0.6–1.3, higher
decays faster. Each number follows from the animal:

- **Riffleback** `[1.15, 0.75, 1.25, 0.7, 0.85]` — burns energy holding station (1.25),
  therefore hungry (1.15), rinsed constantly by fast clean water (0.7), contented (0.75),
  not after novelty (0.85).
- **Sendling** `[1.05, 1.25, 0.75, 0.8, 1.2]` — the current does the work (0.75), so it
  is the exact mirror; restless when nothing is moving (1.25), never anywhere long enough
  to get dirty (0.8), needs constant new input (1.2).
- **Tallymite** `[0.8, 0.9, 1.25, 1.15, 1.25]` — never stops walking (1.25); it touches
  every surface including the filthy ones (1.15); an indexer with nothing left to index
  goes dull fast (1.25); it barely eats (0.8).
- **Shinglecoat** `[1.1, 0.7, 0.75, 1.2, 0.85]` — slow and deliberate (0.75, mirroring
  Tallymite), deeply contented because it has its things (0.7), lives in silt (1.2),
  carrying a heavy coat costs it (1.1), wants the same stones rather than new ones (0.85).

`hungryFor` follows from what each animal is, not from a food table: Riffleback eats
"whatever drifts past" because that is what a station-holding fish does; Tallymite eats
"unswept corners" because it feeds on what it has not yet been over; Shinglecoat eats
"the green off stones" because it is a stream-bed grazer; Sendling eats "loose bytes"
because it grazes on whatever the stream is carrying.

No description mentions a stat, a need, a meter, spawn odds or any other mechanic.

## Weights

52 / 50 / 44 / 46. All four are ordinary wild rolls from day one, in the band the live
roster already uses (45–70). No gating attempted — the expedition ladder does not exist
yet and is another lane's work.

**Earned-unlock nomination: Tallymite.** Two reasons. It has the most *specialist* stat
line in the batch — two +5s paid for with three negatives — and a specialist is the right
shape to gate, while generalists should be day-one so a new player's first rolls are
varied. And its whole identity is completing an exhaustive sweep, which is what an
expedition ladder asks a player to do; "will finish the sweep, it has always finished the
sweep" is a better reward line than an opening line. Shinglecoat is the tempting
alternative because it is thematically a collector, but it is warm and immediately
likeable, which is exactly what a new roster needs early.

## Rejected along the way

- **`X` (pattern ink) for markings.** Drawn first and rejected by the validator: `X` is in
  the v2 role alphabet but **not** in the v1 `feature` legend (`.OBSAEWMC#`). Worth
  knowing that the shipped builtin overlays *do* use it — `GlitchfinSliceAdult` and
  `PrismiteAntlersAdult` both spell `X` — so compiled-in overlays are drawn from a wider
  alphabet than a content pack is allowed. Not a blocker, and stricter is the safe
  direction, but it means pack species cannot use the ink role that builtins mark with.
- **Dark `O` mottling and vertical dark bars on the fish.** Rendered and looked at: next
  to the tail-base outline (`x11`, dark in both stages) they merge into what reads as a
  gash, and isolated single dark cells on a pale body read as holes or bruises rather
  than markings — one landed beside the eye and read as a black eye. Replaced with pale
  `S` marks, which also dropped dark ink from ~43% to ~34%.
- **Accent (`A`) masses on top of the fish.** A 3×2 block of accent above the head reads
  as a hat, not a fin, and because `A` is a DNA-chosen colour it is a hat in an arbitrary
  colour. Cut back to the archetype's own idiom — a small fin, plus a single-cell tip on
  Sendling to break the slab.
- **A trailing motion streak behind Sendling's tail.** The keyline ring is measured off
  the 4-neighbourhood of *any* non-transparent cell, so detached dashes come back as
  ringed dots, and the cell that would carry them is background on one stage and outline
  on the other. Abandoned; the motion is carried by the horizontal streaks instead.
- **Notching the fish tail with `#` to fork it.** Cutting `(12,7)`–`(12,8)` forks the
  Adult nicely and leaves a two-cell **floating island** on the Teen. Caught by a
  connectivity check rather than by eye. A single-row cut survives both but is invisible
  at this size, so it earned nothing and was dropped.
- **Barbels on Riffleback, and a low pectoral fin.** Both wanted a fixed column next to
  the mouth, and the mouth is at `x3` on the Adult and `x5` on the Teen. Anything anchored
  there attaches on one stage and floats on the other.

## The constraint that shaped all four grids

A content pack supplies **one** `feature` overlay and `PalSpriteGrids.RegisterFeature`
applies it to Teen **and** Adult. The builtin species do not have this problem — all
fourteen author a separate Teen and Adult overlay (`CachehogSpikesTeen` /
`CachehogSpikesAdult`, and so on). So a pack species has to find marks that land
correctly on two differently-proportioned bodies.

For `fish` the two stages agree on rows but shift 1–2 columns near the face, and almost
every boundary cell differs, which leaves a silhouette budget of only 1–7 cells. For
`crawler` the carapace (rows 6–8, columns 8–12) is plain body on both stages, which is
why the crawler pair is the stronger of the two: it has somewhere to put a marking that
means something.

Every addition was checked for connectivity on **both** stages before it was kept, and
none of the four grids spends a cell on the frame edge, so the keyline can ring all of
them completely.

## Honest verdict on the art

Tallymite and Shinglecoat clear the bar comfortably and read as what they are named.

The fish pair is the weaker of the two and clears it only marginally. The `fish`
archetype's Teen and Adult are round and cheeky and already wear a small accent nub on
top, so an overlay has little room to add anatomy without reading as an applied sticker;
both fish read as *plausible round fish with distinct markings* rather than as
unmistakable river fish. They carry no structural failures — nothing floating, nothing
welded that should be free, morphology consistent across stages, dark ink around 34% —
and the pair reads as counterparts when the two are seen together. If a reviewer wants
the fish to read harder as fish, the honest fix is a **v2** pair with their own stage
grids rather than more work on a v1 overlay, and that is a scope decision, not a redraw.
