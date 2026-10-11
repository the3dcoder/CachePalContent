#!/usr/bin/env python3
"""build-drop — assemble a weekly drop from the approved BarnQueue pool.

Part of the weekly-drop pipeline (CachePal docs/plan/WEEKLY_DROP_RUNBOOK.md).
Reads APPROVED rows and turns them into species/*.json sources, ready for
`palpack.mjs validate` + `publish`:

  1. species-submission rows → new cachepal-pack-v2 species files:
     append-only ids after the current registry max. A version 2 row (the
     Studio from studio-v2, 2026-10-11: `"version": 2`) carries the maker's
     colours, archetype, hungryFor, needDecayBias and three stage lines, so
     nothing is written by hand; a version 1 row still needs an overlay file
     for them (--overlays). Every row's painted overlays and second frames
     (gridBabyB…gridElderB) go into the pack as the maker painted them.
     First-egg phrase (premiereSeed) = requestedSeed or "<name> premiere",
     minted once through the CachePal FreezeHarness to prove it mints for the
     new id; createdBy + history seeded. The minted DNA is written nowhere: a
     DNA is a clone code and every file here is served (tools/dna-scan.py), so
     the game mints the first egg from the phrase itself.
  2. dex-edit rows → weight/lore/retire/delist applied to their target species files,
     folded oldest→newest (latest wins per field; retire pins weight 0 —
     the SAME net state the /admin/dex staged overlay showed), history
     entries appended.

Usage:
  AZURE_STORAGE_CONNECTION_STRING='…' python3 tools/build-drop.py \
      --cachepal-root /home/user/CachePal [--overlays <dir>] [--drop-tag 2026-W30] \
      [--manifest <file>] [--rows <file>]

  --overlays is needed only when a version 1 row is approved.
  --manifest writes the rows this run built, as JSON: what tools/drop.py stamps
    PublishedAt on, and writes the drop notes from. [] when nothing was built.
  --rows reads the approved pool from a file (the az query's "items" list, or the
    list itself) instead of the queue: a rehearsal with no queue at all.
  Checks: python3 tools/test_build_drop.py (throwaway copies, stub az and dotnet).

The whole drop is one command, tools/drop.py, which runs this. By hand: palpack
validate → publish-drop.sh → close the loop on the queue rows with the printed az
commands (the Reason tells the maker their first-egg phrase).
Idempotent: species already in the registry are skipped.
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Every stage grid a pack species can carry, required and optional alike. The elder is optional
# (B26/Q8) and absent from most species, which is exactly why it needs naming here: code that
# walked "the grids this revision sent" instead of "the grids a species can have" could not see an
# elder being removed, and code that listed the required three by hand simply forgot it (B641).
GRID_KEYS = ("gridBaby", "gridTeen", "gridAdult", "gridElder")

# Version 2 (studio-v2): the maker's choices, spelled as the pack spells them, so they are copied
# verbatim. CachePal's SpeciesSubmission.TryValidate holds each to the Studio's lists before a row
# can be filed; a new species' row carries all eight, a revision any of them.
CHOICE_KEYS = ("baseColor", "shinyColor", "bodyArchetype", "hungryFor", "needDecayBias",
               "babyDescription", "teenDescription", "adultDescription")
LINE_KEYS = ("babyDescription", "teenDescription", "adultDescription")
# The second animation frames. Absent is none: frame A plays alone.
FRAME_KEYS = ("gridBabyB", "gridTeenB", "gridAdultB", "gridElderB")
# What each choice is called in a revision's history entry.
CHOICE_WORDS = {"baseColor": "colours", "shinyColor": "colours", "bodyArchetype": "shape",
                "hungryFor": "appetite", "needDecayBias": "appetite", "babyDescription": "lines",
                "teenDescription": "lines", "adultDescription": "lines"}


def present(value) -> bool:
    """A value a row really carries: not null, not blank, not an empty list."""
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, list):
        return len(value) > 0
    return True


def is_v2(sub: dict) -> bool:
    return sub.get("version") == 2


def choice(sub: dict, key: str):
    value = sub[key]
    return value.strip() if key in LINE_KEYS else value


def choices_of(sub: dict, name: str) -> dict:
    """A version 2 new species' choices: all eight, or the row is refused (never guessed at)."""
    missing = [k for k in CHOICE_KEYS if not present(sub.get(k))]
    if missing:
        raise SystemExit(f"INCOMPLETE VERSION 2 ROW for {name}: {', '.join(missing)} missing. The Barn's rulebook "
                         "refuses such a row, so it was filed some other way: reject it in /admin.")
    return {k: choice(sub, k) for k in CHOICE_KEYS}


def painted(sub: dict) -> dict:
    """The art a row carries beyond the stage grids, as the maker painted it: second frames and overlays."""
    out = {k: sub[k] for k in FRAME_KEYS if present(sub.get(k))}
    if present(sub.get("overlays")):
        out["overlays"] = sub["overlays"]
    return out


ROWS_FILE: str | None = None  # --rows: the approved pool from a file, not the queue


def az_query(filter_: str, select: str | None = None) -> list[dict]:
    if ROWS_FILE is not None:
        data = json.loads(Path(ROWS_FILE).read_text())
        items = data.get("items", []) if isinstance(data, dict) else data
        kind = re.search(r"Type eq '([a-z-]+)'", filter_)
        return [r for r in items if r.get("Status") == "approved" and (not kind or r.get("Type") == kind.group(1))]
    args = ["az", "storage", "entity", "query", "--table-name", "BarnQueue",
            "--filter", filter_, "-o", "json"]
    if select:
        args += ["--select", select]
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"az query failed:\n{result.stderr.strip()}")
    return json.loads(result.stdout).get("items", [])


def registry_species() -> list[dict]:
    reg = json.loads((ROOT / "registry.pub.json").read_text())
    payload = json.loads(base64.urlsafe_b64decode(reg["payload"] + "==="))
    return payload["species"]


def slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9-]", "-", name.lower().replace(" ", "-"))
    return re.sub(r"-+", "-", s).strip("-")


def mint(cachepal_root: str, species_id: int, seed: str) -> str:
    result = subprocess.run(
        ["dotnet", "run", "--project", str(Path(cachepal_root) / "tools/FreezeHarness"), "--",
         "mint", str(species_id), seed],
        capture_output=True, text=True)
    line = (result.stdout.strip().splitlines() or [""])[-1]
    if result.returncode != 0 or line.count("|") != 2:
        raise SystemExit(f"mint failed for {species_id} '{seed}':\n{result.stderr.strip()}")
    return line.split("|")[0]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cachepal-root", required=True)
    ap.add_argument("--overlays", help="dir of <key>.overlay.json files, for version 1 rows")
    ap.add_argument("--drop-tag", default=datetime.now(timezone.utc).strftime("%G-W%V"))
    ap.add_argument("--manifest", help="write the rows this run built here, as JSON")
    ap.add_argument("--rows", help="read the approved pool from this file instead of the queue")
    args = ap.parse_args()
    global ROWS_FILE
    ROWS_FILE = args.rows
    if not args.rows and not os.environ.get("AZURE_STORAGE_CONNECTION_STRING"):
        raise SystemExit("Set AZURE_STORAGE_CONNECTION_STRING first (see runbook step 1), or rehearse with --rows <file>.")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    published = {s["name"].lower() for s in registry_species()}
    next_id = max((s["id"] for s in registry_species()), default=14) + 1
    close_loop: list[str] = []
    shipped: list[dict] = []
    new_species_keys: dict[int, str] = {}

    def stamp(row: dict, reason: str | None = None, **what) -> None:
        """Close-loop merge: PublishedAt clears the /admin/dex staged chip and
        marks the row spent for future runs; Reason is the creator-facing note.
        Each stamped row is also one manifest entry (--manifest)."""
        row_key = row["RowKey"]
        cmd = ("az storage entity merge --table-name BarnQueue --entity "
               f"PartitionKey=q 'RowKey={row_key}' 'PublishedAt={now_iso}'")
        if reason:
            cmd += f" 'Reason={reason}'"
        close_loop.append(cmd)
        shipped.append({"rowKey": row_key, "type": row.get("Type"), "reason": reason, **what})

    # ---- 1. approved submissions → new v2 species files ----------------------
    # B648 — every file path this loop writes, so a second row cannot silently take a first row's.
    claimed_keys: set[str] = set()
    rows = az_query("PartitionKey eq 'q' and Type eq 'species-submission' and Status eq 'approved'")
    for row in sorted(rows, key=lambda r: r["RowKey"], reverse=True):  # oldest first
        sub = json.loads(row["BodyJson"])
        name = sub["name"].strip()
        # B648 — a spent row is skipped by its STAMP, not only by its name. The runbook promises
        # both ("skips species already in the registry AND rows already stamped PublishedAt") and
        # the dex-edit loop below has always checked it; this one matched names against the local
        # registry alone. So a row whose species was later RENAMED by a revision stopped matching
        # and was re-created under its original slug with a fresh id, clobbering the live species
        # file until palpack's append-only check halted the drop at the signing step.
        if row.get("PublishedAt"):
            print(f"SKIP {name} — row already stamped published {row['PublishedAt']}")
            continue

        if name.lower() in published:
            print(f"SKIP {name} — already in the registry")
            continue

        key = slug(name)
        # B648 — the file path IS slug(name), and nothing checked it was free. Uniqueness is
        # enforced on the exact lowercased display NAME (the submit-time duplicate guard, and
        # `published` above), but slug() folds spaces and punctuation to '-', so "Sky Lark" and
        # "Sky-Lark" are two approvable names and one file. In the same drop the first is written
        # and then overwritten by the second — and palpack cannot see it, because its duplicate-id
        # and duplicate-key checks compare distinct FILES and this collision produces only one.
        out = ROOT / "species" / f"{key}.json"
        if key in claimed_keys or out.exists():
            clash = "another approved row in this drop" if key in claimed_keys else "an already-published species"
            raise SystemExit(
                f"REFUSING: '{name}' publishes to species/{key}.json, which {clash} already claims. "
                "Two different display names can slug to the same file. Rename one of them and re-run "
                "— publishing over it would lose a species nobody would see go.")
        claimed_keys.add(key)

        if is_v2(sub):
            # The maker decided what ships: nothing here is written by hand.
            look = choices_of(sub, name)
        else:
            overlay_path = Path(args.overlays or "<--overlays dir>") / f"{key}.overlay.json"
            if not args.overlays or not overlay_path.exists():
                raise SystemExit(f"MISSING OVERLAY for {name}: author {overlay_path} first "
                                 "(colors, archetype, hungryFor, needDecayBias, stage descriptions) — "
                                 "a version 1 row carries none of them.")
            overlay = json.loads(overlay_path.read_text())
            look = {k: overlay[k] for k in CHOICE_KEYS}

        by = row.get("SubmitterName") or "Cache Pal Studio"
        seed = (sub.get("requestedSeed") or "").strip() or f"{name} premiere"
        mint(args.cachepal_root, next_id, seed)  # proves the phrase mints for this id; the DNA goes nowhere
        species = {
            "schema": "cachepal-pack-v2",
            "id": next_id,
            "key": key,
            "name": name,
            "description": sub.get("lore", "").strip(),
            "credit": by,
            "createdBy": by,
            "element": sub.get("element", ""),
            "baseColor": look["baseColor"],
            "shinyColor": look["shinyColor"],
            "bodyArchetype": look["bodyArchetype"],
            "statBias": [sub.get("biasPower", 0), sub.get("biasMischief", 0),
                         sub.get("biasStealth", 0), sub.get("biasResilience", 0),
                         sub.get("biasLuck", 0), sub.get("biasSignal", 0)],
            "hungryFor": look["hungryFor"],
            "needDecayBias": look["needDecayBias"],
            "babyDescription": look["babyDescription"],
            "teenDescription": look["teenDescription"],
            "adultDescription": look["adultDescription"],
            "weight": sub.get("suggestedWeight", 60),
            "gridBaby": sub["gridBaby"],
            "gridTeen": sub["gridTeen"],
            "gridAdult": sub["gridAdult"],
            # B641 — the elder is optional (B26/Q8), so it is written by PRESENCE: absent when the
            # creator left the fourth canvas blank, which is what makes elders fall back to the
            # adult. It was written by nothing at all until now, so a creator who did draw one had
            # it silently dropped on the way to the pack — while the Studio told them, at
            # Studio.razor:466, that leaving it blank is what makes the adult stand in.
            **({"gridElder": sub["gridElder"]} if sub.get("gridElder") else {}),
            # studio-v2 — the second frames and the overlays the maker painted. Dropped until now:
            # the Studio drew them, the reviewer approved them, and the pack never carried them.
            **painted(sub),
            "premiereSeed": seed,
            "history": [{"date": today, "change": f"created (drop {args.drop_tag})", "by": by}],
        }
        out.write_text(json.dumps(species, indent=2, ensure_ascii=False) + "\n")
        print(f"WROTE {out.name}: id {next_id}, first-egg phrase '{seed}' (by {by})")
        stamp(row, f"Published in drop {args.drop_tag} as species {next_id}. Its first-egg phrase: \u201c{seed}\u201d.",
              name=name, key=key, id=next_id, phrase=seed, by=by, element=species["element"],
              lore=species["description"])
        new_species_keys[next_id] = key
        next_id += 1

    # ---- 2. approved dex-edits + revisions → apply oldest-first ---------------
    # One merged pass across BOTH types sorted by CreatedAt (row keys are
    # inverted ticks: larger = older, so reverse-sort = oldest first). A later
    # decision wins a field conflict, and each step appends its own history
    # entry (WAVE6_REVISIONS_NOTES "Applying revisions" §3).
    key_by_id = {s["id"]: s["key"] for s in registry_species()}
    key_by_id.update(new_species_keys)  # same-drop create-then-revise works too

    changes_rows = (az_query("PartitionKey eq 'q' and Type eq 'dex-edit' and Status eq 'approved'")
                    + az_query("PartitionKey eq 'q' and Type eq 'species-revision' and Status eq 'approved'"))
    for row in sorted(changes_rows, key=lambda r: r["RowKey"], reverse=True):  # oldest first
        body = json.loads(row["BodyJson"])
        is_revision = row.get("Type") == "species-revision"
        sid = body["targetSpeciesId"] if is_revision else body["speciesId"]
        key = key_by_id.get(sid)
        if key is None:
            print(f"WARN {row.get('Type')} targets unknown species {sid} — skipped")
            continue
        path = ROOT / "species" / f"{key}.json"
        species = json.loads(path.read_text())
        changed: list[str] = []

        if row.get("PublishedAt"):
            print(f"SKIP {row.get('Type')} for {key} — already published {row['PublishedAt']}")
            continue

        if is_revision:
            by = row.get("SubmitterName") or "someone"
            new_grids = {g: body[g] for g in ("gridBaby", "gridTeen", "gridAdult")}
            if body.get("gridElder"):
                new_grids["gridElder"] = body["gridElder"]
            # B641 — compared across the UNION, not across the revision's own keys. Iterating
            # `new_grids` alone made one art edit invisible: clearing the elder removes the key, so
            # there was nothing left to compare and the drop reported "touched up".
            if any(species.get(g) != new_grids.get(g) for g in GRID_KEYS):
                changed.append("first custom art" if "gridBaby" not in species else "art")
            for src, dst in (("name", "name"), ("lore", "description"), ("element", "element")):
                if body.get(src, "").strip() and body[src].strip() != species.get(dst, ""):
                    changed.append(src if src != "lore" else "lore")
            biases = [body.get("biasPower", 0), body.get("biasMischief", 0),
                      body.get("biasStealth", 0), body.get("biasResilience", 0),
                      body.get("biasLuck", 0), body.get("biasSignal", 0)]
            if biases != species.get("statBias"):
                changed.append("biases")
            if body.get("suggestedWeight") != species.get("weight"):
                changed.append("weight")
            # studio-v2 — the choices a version 2 revision gives replace the live ones; one it leaves
            # out keeps the live one (the Studio leaves a live value off its lists unpicked).
            choices = {k: choice(body, k) for k in CHOICE_KEYS if is_v2(body) and present(body.get(k))}
            for k, v in choices.items():
                if species.get(k) != v and CHOICE_WORDS[k] not in changed:
                    changed.append(CHOICE_WORDS[k])
            # The second frames: a version 2 row carries every one the Pal has (the Studio opens the
            # live ones on frame 2), so an absent one is none — an old pose would not fit new art. A
            # version 1 row never carried them and leaves them as they are.
            frames = {k: body[k] for k in FRAME_KEYS if present(body.get(k))} if is_v2(body) else None
            if frames is not None and any(species.get(k) != frames.get(k) for k in FRAME_KEYS):
                changed.append("frames")
            # The overlays: every row filed since the Studio drew them carries the whole set (an empty
            # list when there are none); a row from before them has no key, and leaves them alone.
            carries_overlays = "overlays" in body
            overlays = body["overlays"] if present(body.get("overlays")) else None
            if carries_overlays and species.get("overlays") != overlays:
                changed.append("overlays")
            # Replace display/data fields; id, key, premiere*, createdBy and (unless a version 2
            # row gives them) the publish-only fields (colors/archetype/hungryFor/decay/stage lines)
            # stay — creator credit is permanent, decode never reads display.
            species.update({
                "schema": "cachepal-pack-v2",
                "name": body["name"].strip(),
                "description": body.get("lore", "").strip(),
                "element": body.get("element", species.get("element", "")),
                "statBias": biases,
                "weight": body.get("suggestedWeight", species.get("weight", 60)),
                **new_grids,
                **choices,
            })
            if frames is not None:
                for k in FRAME_KEYS:
                    if k in frames:
                        species[k] = frames[k]
                    else:
                        species.pop(k, None)
            if carries_overlays:
                if overlays is None:
                    species.pop("overlays", None)
                else:
                    species["overlays"] = overlays
            # B641 — `update()` adds and replaces but never removes, so an elder the revision
            # cleared has to be dropped by hand. Without this the species keeps publishing a life
            # stage its creator deleted, and no later revision can ever take it off.
            if "gridElder" not in new_grids:
                species.pop("gridElder", None)
            entry_change = f"revised: {', '.join(changed) if changed else 'touched up'}"
            species.setdefault("history", []).append(
                {"date": today, "change": entry_change, "by": by})
            stamp(row, f"Published in drop {args.drop_tag} — {entry_change}",
                  name=species["name"], key=key, id=sid, change=entry_change, by=by)
        else:
            if body.get("retire"):
                species["weight"] = 0
                changed.append("retired (weight 0)")
            elif body.get("weight") is not None:
                species["weight"] = body["weight"]
                changed.append(f"weight → {body['weight']}")
            if body.get("lore") is not None:
                species["description"] = body["lore"]
                changed.append("lore updated")
            if body.get("delist"):
                # B62: the Barn can only file the INTENT — `delisted` lives inside the
                # signed registry payload, so this is where it becomes real. Same effect
                # as `palpack.mjs delist`, which is the fast path for an urgent takedown.
                # The public history entry stays neutral: the why belongs in the private
                # moderation log, not on a page served to every player.
                species["delisted"] = True
                changed.append("DELISTED (stops reaching new devices; owners keep theirs)")
            species.setdefault("history", []).append(
                {"date": today, "change": f"dex-edit: {', '.join(changed)} (drop {args.drop_tag})",
                 "by": "operator"})
            stamp(row, None, name=species["name"], key=key, id=sid,
                  change=f"dex-edit: {', '.join(changed)}")  # clears its 🌾 staged chip in /admin/dex

        path.write_text(json.dumps(species, indent=2, ensure_ascii=False) + "\n")
        print(f"{'REVISED' if is_revision else 'EDITED'} {path.name}: {', '.join(changed) or 'no visible change'}")

    if args.manifest:
        Path(args.manifest).write_text(json.dumps(shipped, indent=2, ensure_ascii=False) + "\n")
    print("\nNext: node tools/palpack.mjs validate && ./tools/publish-drop.sh <count> (tools/drop.py does all of it)")
    if close_loop:
        print("\nClose the loop after publish + push:")
        for cmd in close_loop:
            print(" ", cmd)


if __name__ == "__main__":
    main()
