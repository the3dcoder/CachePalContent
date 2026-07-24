#!/usr/bin/env python3
"""build-drop — assemble a weekly drop from the approved BarnQueue pool.

Part of the weekly-drop pipeline (CachePal docs/plan/WEEKLY_DROP_RUNBOOK.md).
Reads APPROVED rows and turns them into species/*.json sources, ready for
`palpack.mjs validate` + `publish`:

  1. species-submission rows → new cachepal-pack-v2 species files:
     append-only ids after the current registry max, overlay file for the
     publish-only fields (colors/archetype/hungryFor/decay/stage lines),
     premiere seed = requestedSeed or "<name> premiere", premiere DNA minted
     via the CachePal FreezeHarness, createdBy + history seeded.
  2. dex-edit rows → weight/lore/retire applied to their target species files,
     folded oldest→newest (latest wins per field; retire pins weight 0 —
     the SAME net state the /admin/dex staged overlay showed), history
     entries appended.

Usage:
  AZURE_STORAGE_CONNECTION_STRING='…' python3 tools/build-drop.py \
      --cachepal-root /home/user/CachePal --overlays <dir> [--drop-tag 2026-W30]

Then: palpack validate → PALPACK_KEY=… palpack publish → git push → close the
loop on the queue rows with the printed az commands (reason = founder seed).
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


def az_query(filter_: str, select: str | None = None) -> list[dict]:
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
    ap.add_argument("--overlays", required=True, help="dir of <key>.overlay.json files")
    ap.add_argument("--drop-tag", default=datetime.now(timezone.utc).strftime("%G-W%V"))
    args = ap.parse_args()

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    published = {s["name"].lower() for s in registry_species()}
    next_id = max((s["id"] for s in registry_species()), default=14) + 1
    close_loop: list[str] = []
    new_species_keys: dict[int, str] = {}

    def stamp(row_key: str, reason: str | None = None) -> None:
        """Close-loop merge: PublishedAt clears the /admin/dex staged chip and
        marks the row spent for future runs; Reason is the creator-facing note."""
        cmd = ("az storage entity merge --table-name BarnQueue --entity "
               f"PartitionKey=q 'RowKey={row_key}' 'PublishedAt={now_iso}'")
        if reason:
            cmd += f" 'Reason={reason}'"
        close_loop.append(cmd)

    # ---- 1. approved submissions → new v2 species files ----------------------
    rows = az_query("PartitionKey eq 'q' and Type eq 'species-submission' and Status eq 'approved'")
    for row in sorted(rows, key=lambda r: r["RowKey"], reverse=True):  # oldest first
        sub = json.loads(row["BodyJson"])
        name = sub["name"].strip()
        if name.lower() in published:
            print(f"SKIP {name} — already in the registry")
            continue

        key = slug(name)
        overlay_path = Path(args.overlays) / f"{key}.overlay.json"
        if not overlay_path.exists():
            raise SystemExit(f"MISSING OVERLAY for {name}: author {overlay_path} first "
                             "(colors, archetype, hungryFor, needDecayBias, stage descriptions).")
        overlay = json.loads(overlay_path.read_text())

        by = row.get("SubmitterName") or "Cache Pal Studio"
        seed = (sub.get("requestedSeed") or "").strip() or f"{name} premiere"
        dna = mint(args.cachepal_root, next_id, seed)
        species = {
            "schema": "cachepal-pack-v2",
            "id": next_id,
            "key": key,
            "name": name,
            "description": sub.get("lore", "").strip(),
            "credit": by,
            "createdBy": by,
            "element": sub.get("element", ""),
            "baseColor": overlay["baseColor"],
            "shinyColor": overlay["shinyColor"],
            "bodyArchetype": overlay["bodyArchetype"],
            "statBias": [sub.get("biasPower", 0), sub.get("biasMischief", 0),
                         sub.get("biasStealth", 0), sub.get("biasResilience", 0),
                         sub.get("biasLuck", 0), sub.get("biasSignal", 0)],
            "hungryFor": overlay["hungryFor"],
            "needDecayBias": overlay["needDecayBias"],
            "babyDescription": overlay["babyDescription"],
            "teenDescription": overlay["teenDescription"],
            "adultDescription": overlay["adultDescription"],
            "weight": sub.get("suggestedWeight", 60),
            "gridBaby": sub["gridBaby"],
            "gridTeen": sub["gridTeen"],
            "gridAdult": sub["gridAdult"],
            "premiereSeed": seed,
            "premiereDna": dna,
            "history": [{"date": today, "change": f"created (drop {args.drop_tag})", "by": by}],
        }
        out = ROOT / "species" / f"{key}.json"
        out.write_text(json.dumps(species, indent=2, ensure_ascii=False) + "\n")
        print(f"WROTE {out.name}: id {next_id}, premiere '{seed}' → {dna} (by {by})")
        stamp(row["RowKey"],
              f"Published in drop {args.drop_tag} as species {next_id} — founder seed: {dna}")
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
            if any(species.get(g) != new_grids[g] for g in new_grids):
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
            # Replace display/data fields; id, key, premiere*, createdBy and the
            # overlay-only fields (colors/archetype/hungryFor/decay/stage lines)
            # stay — creator credit is permanent, decode never reads display.
            species.update({
                "schema": "cachepal-pack-v2",
                "name": body["name"].strip(),
                "description": body.get("lore", "").strip(),
                "element": body.get("element", species.get("element", "")),
                "statBias": biases,
                "weight": body.get("suggestedWeight", species.get("weight", 60)),
                **new_grids,
            })
            entry_change = f"revised: {', '.join(changed) if changed else 'touched up'}"
            species.setdefault("history", []).append(
                {"date": today, "change": entry_change, "by": by})
            stamp(row["RowKey"], f"Published in drop {args.drop_tag} — {entry_change}")
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
            species.setdefault("history", []).append(
                {"date": today, "change": f"dex-edit: {', '.join(changed)} (drop {args.drop_tag})",
                 "by": "operator"})
            stamp(row["RowKey"])  # clears its 🌾 staged chip in /admin/dex

        path.write_text(json.dumps(species, indent=2, ensure_ascii=False) + "\n")
        print(f"{'REVISED' if is_revision else 'EDITED'} {path.name}: {', '.join(changed) or 'no visible change'}")

    print("\nNext: node tools/palpack.mjs validate && PALPACK_KEY=… node tools/palpack.mjs publish")
    if close_loop:
        print("\nClose the loop after publish + push:")
        for cmd in close_loop:
            print(" ", cmd)


if __name__ == "__main__":
    if not os.environ.get("AZURE_STORAGE_CONNECTION_STRING"):
        raise SystemExit("Set AZURE_STORAGE_CONNECTION_STRING first (see runbook step 1).")
    main()
