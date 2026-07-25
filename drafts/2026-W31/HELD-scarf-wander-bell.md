# Wander Bell — decided, now waiting only on the client floor

**Decision, 2026-07-25 (owner):** price it as a **rare, 900 coins**, and rewrite the lore so
the name describes something the game actually does — the piece is only purchasable on *some*
weeks. It wanders.

That closes the collision described below. It no longer competes with `scarf-thirty-winters`
for milestone `elder-1`, and it now has exactly one acquisition path, as the rulebook requires.

What it still waits on is **B78**, not a decision: any client older than v1.8.1 drops a
cosmetic-carrying pack whole, so publishing it early would make its carrying species invisible
again (`docs/PACK_FORMAT.md`, D57). It ships when v1.8.1 is the floor build in the wild.

It also waits on the wandering-stock mechanic being live, because otherwise the lore promises
behaviour the shop does not have — which is the same class of mistake as the `v@AppVersion`
literal and the "fail-soft" comment that could not fail soft. Text and behaviour ship together
or neither ships.

---

## The collision this file originally recorded

This piece was drafted as the content half of a *reserved wardrobe slot*: content packs cannot
add milestone entries (`MilestoneCatalog` is compiled), so a pack cosmetic can only hang off a
milestone key the shipped game already knows. The draft proposed `elder-1`, and the game did
not have it yet.

`elder-1` then shipped compiled with a piece of its own, `scarf-thirty-winters`, because a
milestone entry with no piece behind it is inert and BarnCheck's `W7` block asserts that every
compiled trophy is winnable. Both scarves pointed at the same milestone, which would have
granted two at once for a single achievement — and this piece's lore promised "thirty days in
your care" while the compiled predicate deliberately ignores liveness, so the text would have
described a condition the code does not enforce, permanently, in an append-only registry.

The compiled piece kept the slot because it was already live: any keeper with a thirty-day-old
Pal is granted it on their next sweep, and revoking an earned trophy is the exact failure the
monotonic predicate exists to prevent.
