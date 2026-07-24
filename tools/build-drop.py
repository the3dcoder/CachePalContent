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
    published = {s["name"].lower() for s in registry_species()}
    next_id = max((s["id"] for s in registry_species()), default=14) + 1
    close_loop: list[str] = []

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
        close_loop.append(
            "az storage entity merge --table-name BarnQueue --entity "
            f"PartitionKey=q 'RowKey={row['RowKey']}' "
            f"'Reason=Published in drop {args.drop_tag} as species {next_id} — "
            f"founder seed: {dna}'")
        next_id += 1

    # ---- 2. approved dex-edits → fold onto their targets ---------------------
    edits = az_query("PartitionKey eq 'q' and Type eq 'dex-edit' and Status eq 'approved'")
    by_species: dict[int, list[dict]] = {}
    for row in sorted(edits, key=lambda r: r["RowKey"], reverse=True):  # oldest first
        body = json.loads(row["BodyJson"])
        by_species.setdefault(body["speciesId"], []).append(body)

    reg_by_id = {s["id"]: s for s in registry_species()}
    for sid, bodies in by_species.items():
        entry = reg_by_id.get(sid)
        if entry is None:
            print(f"WARN dex-edit targets unknown species {sid} — skipped")
            continue
        path = ROOT / "species" / f"{entry['key']}.json"
        species = json.loads(path.read_text())
        changes = []
        for body in bodies:  # oldest→newest: the latest staging wins per field
            if body.get("retire"):
                species["weight"] = 0
                changes.append("retired (weight 0)")
            elif body.get("weight") is not None:
                species["weight"] = body["weight"]
                changes.append(f"weight → {body['weight']}")
            if body.get("lore") is not None:
                species["description"] = body["lore"]
                changes.append("lore updated")
        species.setdefault("history", []).append(
            {"date": today, "change": f"dex-edit: {', '.join(changes)} (drop {args.drop_tag})",
             "by": "operator"})
        path.write_text(json.dumps(species, indent=2, ensure_ascii=False) + "\n")
        print(f"EDITED {path.name}: {', '.join(changes)}")

    print("\nNext: node tools/palpack.mjs validate && PALPACK_KEY=… node tools/palpack.mjs publish")
    if close_loop:
        print("\nClose the loop after publish + push:")
        for cmd in close_loop:
            print(" ", cmd)


if __name__ == "__main__":
    if not os.environ.get("AZURE_STORAGE_CONNECTION_STRING"):
        raise SystemExit("Set AZURE_STORAGE_CONNECTION_STRING first (see runbook step 1).")
    main()
