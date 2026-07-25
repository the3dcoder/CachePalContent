# Wander Bell — HELD from drop 2026-W31

Held for one reason, and it is not the art: **its milestone slot was taken before the
drop went out, by the operator side, and the piece cannot ship as drafted.**

## What happened

This piece was drafted as the content half of a *reserved wardrobe slot*: content packs
cannot add milestone entries (`MilestoneCatalog` is compiled), so a pack cosmetic can
only hang off a milestone key the shipped game already knows. The draft proposed
`elder-1` and the game did not have it yet.

`elder-1` then shipped compiled in **v1.8.0** — with a piece of its own,
`scarf-thirty-winters` — because a milestone entry with no piece behind it is inert and
BarnCheck's `W7` block asserts that every compiled trophy is winnable. Both scarves now
point at the same milestone.

## Why not just ship it anyway

- **Two rewards for one achievement, both scarves.** `WardrobeService`'s sweep grants
  every unowned item whose predicate is true, so earning `elder-1` would hand over both
  and a Pal can wear one.
- **The lore and the shipped predicate disagree.** This piece promises "thirty days in
  your care" and its draft rationale specifies `IsElder && IsAlive`. The compiled
  predicate is deliberately `IsElder` alone and monotonic — an offline catch-up can cross
  elderhood and death inside one fast-forward, and the liveness test would let a player
  earn and lose a trophy in the same silent tick. So the shipped condition is *not* what
  this text describes, and content is append-only: a signed lore line cannot be recalled.

## Why the compiled piece is the one that stays

`scarf-thirty-winters` is live. Any keeper who already has a thirty-day-old Pal is
granted it on their next sweep, and revoking an earned trophy is exactly the failure the
monotonic predicate exists to prevent. The live one wins by default, not by merit.

## The two ways this piece can land, both cheap

1. **Coin-priced rare (900), with one lore line rewritten** so it no longer claims an
   achievement. The wardrobe genuinely lacks what this piece is — every shipped scarf is
   a broad woven band and this one reads as jewelry — and the art needs no change:
   44/44 cells verified across 27 archetype × stage combinations, 42/44 on shell.
2. **A new compiled milestone in the next game release**, with this piece as its content
   half and a hint that matches whatever predicate actually ships. That restores the
   reserved-slot design the draft was written for.

Owner's call, because it decides what a reward *means* rather than how it works. Nothing
is lost by waiting: the piece keeps, and the drop shipped without it.
