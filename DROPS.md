# Content drops

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
