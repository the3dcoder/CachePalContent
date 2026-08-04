# Content drops

## Generation 9 — 2026-07-29 · Drop 2026-W31 ("Two Small Comforts")

A wardrobe-only drop, and the first publish under B205's guards.

**Enamel Mug** (`hat-enamel-mug`, hat, common, 🪙120)
_Navy rim, one chip, and more tea through it than most cupboards see in a
lifetime. Retired to a warmer job._ ☕

**Yarn End** (`scarf-yarn-end`, scarf, common, 🪙120)
_Too short for the row it was meant for. Too good to throw out._ 🧶

Both were authored and gated in the app repo by `W68-DROP`, which assembles
them into the canonical bytes `publish` emits and reads them back through the
shipped `WardrobeFile.Read`, **counted** — both channel readers are fail-soft
by design, so a rejected piece is silent, and "it did not throw" is the
posture that cost generation 4 two species. Hat and scarf rather than props on
purpose: the shop's tier-heading branches exclude props and the priced ladder
stops at Rare, so a coin relic prop would render as a bare tile with no
heading and a dead tap target. Filling that cell is an app release, not a drop.

**What the guards reported, and why the third line is the point:**

```
freshness:   baseline generation 8 byte-identical to the live registry
append-only: backgrounds 1 → 1 entry, none removed
append-only: wardrobe   1 → 3 entries, none removed
append-only: 6 species and 2 channels compared against generation 8
```

Wave 40 came one command short of publishing from a generation-7 clone whose
`palpack.mjs` contained zero references to backgrounds. That would have
re-issued an already-signed generation **and silently unpublished Lantern
Thicket** — a 900-coin background — for everyone who had bought it, with no
error anywhere. The channel guard now derives its set from the previous
payload's own keys rather than a named list of two, and the freshness gate
refuses any clone that is not byte-identical to live.

Verified live after publish: registry reports generation 9, the cosmetics file
carries all three pieces (both new ones and The Lamplighter), and the
backgrounds channel still answers 200.


## Generation 1 — 2026-07-23

**Emberimp** (species 14) — premiere code: `e1f20c80-000e-c5e0-5f54-29a6afd8f631`
Paste it in the Hatchery seed box (requires app content sync — the app fetches
this repo automatically). Weekly weight-table rolls arrive with the next app
release; until then the premiere code is the only wild source. 🔥

## Generation 3 — 2026-07-24 · Drop 2026-W30 ("First Weekly Drop")

The first drop assembled through the Barn queue: filed → operator-approved
in /admin → signed. Custom 3-stage art debuts (pack v2).

**Thistledown** (species 15, Bloom) — premiere code: `e0915087-000f-c9ad-88cf-33c76fb4819c`
_A wandering tuft that collects overheard wishes._ Founder phrase: "make a wish" 🌾

**Puddlejack** (species 16, Tide) — premiere code: `5f9cbe7b-0010-c9b0-0315-a7d139d76a54`
_A puddle that jumped back._ Founder phrase: "after the rain" 💧

**Glowtail** (species 17, Neon) — premiere code: `b3ce4dbe-0011-cf70-1a1b-498cd46fdebb`
_A neon gecko whose tail writes names in the dark._ Founder phrase: "night market" ✨

Also in this drop: **Emberimp** weight 60 → 69 + lore touch-up (dex-edit,
first staged-pool publish). Paste any premiere code in the Hatchery seed box
(content sync fetches this repo automatically).

## Generation 4 — 2026-07-25 · Drop 2026-W31 ("Logbook and Fog")

Two species, and the **first content-delivered cosmetics** ever to ship: pieces
now ride a v2 species pack as an additive field, exactly as v1.7 designed and
nobody had yet used.

**Latchback** (species 18, Alloy) — premiere code: `3f5b0022-0012-cd25-4ecd-1c7a8005c4e6`
_A walking strongbox that files everything and returns nothing._ Premiere seed: "sign the logbook" 🧰
Carries **Paper Admiral** (hat, uncommon, 350 coins).

**Hushwing** (species 19, Mist) — premiere code: `ebfdbe91-0013-cecb-7058-58378a025dfa`
_A fog-wader that lifts one wing and the morning goes quiet._ Premiere seed: "quiet as weather" 🌫️
Carries **Moth Hour** (aura, rare, 900 coins) — the first aura with a shape in it
rather than a dither, three moths that never lose a cell on any body at any stage.

Paste either premiere code in the Hatchery seed box; content sync fetches this repo
automatically, and the cosmetics appear in the shop's Style tab once it lands.

> **That last sentence was wrong and this drop was broken.** Neither species appeared for
> anyone and neither cosmetic existed; see generation 5. Left standing rather than quietly
> corrected, because a ledger that edits its own claims after the fact is not a ledger.

Held from this drop, and why, in `drafts/2026-W31/`: **Geodecoil** (art not at the
bar — the adult read as architecture rather than a serpent) and **Wander Bell**
(its milestone slot was filled by a compiled piece in game v1.8.0, so it needs
either a coin price or a new milestone — owner's call).

## Generation 5 — 2026-07-25 · Withdrawal (no new content)

**Generation 4 made Latchback and Hushwing invisible to every live client**, and this
generation is the rollback. No species added, none removed, both cosmetics arrays stripped.

The cause was one missing line, four layers down. `palpack` has always written
`"slot": "hat"` as a string; `System.Text.Json` will not turn a string into an enum without
a `JsonStringEnumConverter`, and the game's sync options did not carry one. So every
cosmetic-carrying pack threw while deserializing — and the throw happened *inside* the
blanket `catch` that wraps whole-pack ingestion, so what got dropped was not the cosmetic
but the species. Both new Pals hatched as dormant mystery eggs.

The documented promise — "a malformed cosmetic is skipped, never sinks its species" — could
not hold, because the failure landed before any per-item code ran. That is now a rule with
teeth rather than a comment: pack cosmetics are read through `Core/Cosmetics/PackCosmetics.cs`
off a raw `JsonElement`, parsed and validated one piece at a time, and no additive pack field
may ever cost a species (game decision D57).

Recorded late: this entry was written with generation 6, because generation 5 shipped as an
emergency and the ledger was not updated at the time. Noting that rather than backdating it.

## Generation 6 — 2026-07-25 · Drop 2026-W31, cosmetics half ("Folded, Moth-lit, Wandering")

The cosmetics from generation 4, re-shipped now that the client that can read them
(**game v1.9.0**) is the one actually running. No species changes — same six ids, same
premiere codes as generation 4; only the two packs carrying wardrobe pieces moved.

**Paper Admiral** — hat, uncommon, 350 coins, on Latchback's pack.
_Folded from yesterday's news. Commands a fleet of one._

**Moth Hour** — aura, rare, 900 coins, on Hushwing's pack. The first aura with a shape in
it rather than a dither: three moths that never lose a cell on any body at any stage.
_They think you're the porch light. Every night, all three of them, absolutely certain._

**Wander Bell** — scarf, rare, 900 coins, on Latchback's pack, and **the first wandering
piece**: it is only in stock roughly one week in three, on a schedule derived from its own
key, never away more than two weeks, and the shop says when it is due back.
_Some weeks the stall has one; most weeks the hook is bare._

Why it is a coin rare rather than the elder trophy it was drafted as: that milestone slot
was taken by a compiled piece in game v1.8.0, and granting two scarves for one achievement
is worse than repricing. The name then earned a mechanic instead of losing one.

Signed only after the *signed pack bytes* were read back through the shipped
`PackCosmetics` reader — every piece parsing, both rares still Rare, the wandering flag
surviving the wire — which is the check generation 4 did not have.

## Generation 7 — 2026-07-25 · The first piece on the wardrobe channel

No species changes. One cosmetic, and it is the first ever delivered by
`cachepal-cosmetics-v1` — the file cosmetics now have to themselves (D61), rather than
riding inside a creature's pack.

**The Lamplighter** — hat, relic, 2600 coins.
_They walked the whole street at dusk so nobody would come home to a dark house. No one
ever thanked them. They went out again the next night._

Hat/Relic was one of only two empty cells in the shop's whole ladder, so this fills a real
hole rather than crowding a full shelf. Requires game **v1.10.0** — older clients skip the
registry's `wardrobe` reference as an unknown field and simply see a shop without it.

Two things about the art are firsts. Its single glint is the one `*` the shipped relics all
carry, so it belongs to the same family as The Long Thread and Signal Lantern. And it is the
only hat in the game that never clips: every painted cell is inside rows 1–4 and columns
4–13, which is the box that survives all nine hat anchors including shell's (−4, +5) — the
offset that shaves a corner off every other hat. Verified against all 27 archetype × stage
combinations, 22 of 22 cells landing on every one.

## Generation 8 — 2026-07-27 · The first scene on the backgrounds channel

No species changes, no cosmetics. One Playground background, and it is the first ever
delivered by `cachepal-backgrounds-v1` — the channel scenes now have to themselves (B90),
built on the same isolation lesson the wardrobe file was (D61): its parse path cannot reach
the species registry, so a bad scene can never cost a creature.

**Lantern Thicket** — Playground background, 900 coins.
_Paper lanterns against the dusk. The fireflies came to see._

Requires game **v1.33.0**. Older clients skip the registry's `backgrounds` reference as an
unknown field and simply see the three compiled scenes, exactly as before.

**The art travels inside the signed file.** A background needs pixels, and the obvious
shape — a URL to this host — was refused: it would add a second fetch path with its own
failure modes, put an unverified remote URL inside a CSS `url()`, and break offline, because
the client caches files rather than downloads. Carrying the PNG as base64 inside the
SHA-256-pinned file means the pixels inherit the registry's Ed25519 chain for free, render
from cache with no network at all, and cannot be swapped by anyone without this key.

**Why this drop waited for a reload rather than a deploy.** The client returns early from a
content sync when the generation is not newer — and that check sits ABOVE the channel
fetches. So a device that had synced generation 8 while still running v1.32.0 would never
have fetched this file at all: not on update, not ever, until generation 9. Nothing would
have errored; the scene simply would not exist. So v1.33.0 went live first, and this was
signed only after the household confirmed it had actually reloaded — the same shape as the
generation 6 wait, for a sharper reason.

`palpack publish` learned the channel in this drop, rather than the reference being pasted
in by hand — a hand-added ref would have been silently dropped by the next publish, which
rebuilds the payload from the repo. `backgrounds/CURRENT` names the live file in one line,
and background keys are now **append-only** for the blunt reason cosmetic keys are: a scene
that vanishes stops resolving, and its owner's Playground heals back to the Meadow. The bag
row survives, so a republished scene returns to whoever bought it — but the thing they paid
for stops appearing, which is the same broken promise a vanished hat would be.

Signed only after the **signed file bytes** were read back through the shipped
`BackgroundFile` reader — one scene, price 900, band and rest spots intact, art arriving as
a data URI — which is the check generation 4 did not have.

## Generation 10 — drop 2026-W32 (2026-08-04)

**Twelve new species, ids 20–31, taking the live roster from twenty to thirty-two.** Six counterpart
pairs — a made thing and a grown thing on the same body plan, opposite in nature — spread across the
archetypes the roster was thinnest in: serpent, jelly, fish, crawler, bloom and shell each had one or
two species and now have three or four.

Eight arrive day-one. **Four are earned** on the expedition ladder, gated as whole pairs rather than
halves: the crawlers (`tallymite`, `shinglecoat`) at the Dusk Market's rung, the shells
(`bramblewick`, `palisade`) at the Chalk Downs'. A pair exists to be read against itself, so gating
one and not the other would hand a keeper half a joke. The rungs are the ladder's own, read through
`MilestoneCatalog` rather than retyped, and the counter behind them sums over every Pal a keeper has
raised INCLUDING THE DEPARTED — a species that appeared on somebody's board must never leave it
because a Pal died.

**Seven species were recoloured, all of them pack-side, and the compiled roster was not touched.**
Four for canonical separation: `glowtail`, `hushwing`, `latchback`, `thistledown` sat below
`W64-ROSTER`'s dE00 bar of 10 against species they could genuinely be confused with, the worst pair
at 5.0 — near the just-noticeable difference. Those six collisions had existed since the registry
began and nothing had ever measured them, because `W64` enumerated only the fourteen COMPILED
species. It now reads the content repo too (B343).

Three more for something a canonical measurement cannot see. `W64`'s group C sweeps every species
across its whole ±30° hue range and requires it to stay a just-noticeable difference from every
other species AT REST — and a hue-shifted `glitchfin` read as `sendling` at **0.7** and as
`puddlejack` at **1.5**. A mutated Pal that looks like a different species. Twenty-eight crossings
across eight directed pairs, all in one blue/cyan cluster, cleared by moving `sendling`, `pilotwire`
and `puddlejack`.

**Why this drop was signed twice.** The first attempt produced a generation 10 containing SIX
species while eighteen were being published: the session's working copy was reverted underneath the
tool between `validate` (which counted 18) and `publish` (which read 6). Every existing gate was
satisfied, because they all ask whether the tree is internally consistent and current against the
live registry, and a smaller tree is both. Nothing reached the CDN only because the push had not
happened — luck, not a control.

`palpack publish` now REFUSES an unpinned tree: `PALPACK_EXPECT_COMMIT` and
`PALPACK_EXPECT_SPECIES` must be set, and both are re-checked immediately before the first byte is
written, because the whole point is that the tree can move mid-run. The commit is the pin rather
than the count alone, since eighteen species can be the wrong eighteen. Attack-proven three ways
before this drop was signed with it.
