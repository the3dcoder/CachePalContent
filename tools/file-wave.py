#!/usr/bin/env python3
"""file-wave — file first-party species submissions into BarnQueue as PENDING rows.

Part of the weekly-drop pipeline (CachePal docs/plan/WEEKLY_DROP_RUNBOOK.md):
first-party waves ride the SAME queue as community submissions, so the operator
approves everything in /admin and the publish step reads one pool.

Usage:
  AZURE_STORAGE_CONNECTION_STRING='<from az storage account show-connection-string>' \
    python3 tools/file-wave.py <submission.json> [...]

Row shape mirrors the Studio API's InsertQueueRowAsync exactly (inverted-ticks
row key, denormalized Name/RequestedSeed/GridsHash/LoreHash for the duplicate
defense). Idempotent: skips any species whose Name already has a queue row.
"""

import hashlib
import json
import os
import secrets
import subprocess
import sys
import time
from datetime import datetime, timezone

MAX_TICKS = 3155378975999999999  # DateTimeOffset.MaxValue.UtcTicks
UNIX_EPOCH_TICKS = 621355968000000000
TABLE = "BarnQueue"
SUBMITTER_NAME = "Cache Pal Studio"


def az(*args: str) -> str:
    result = subprocess.run(["az", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"az {' '.join(args[:3])}… failed:\n{result.stderr.strip()}")
    return result.stdout


def grids_hash(sub: dict) -> str:
    joined = ("\n".join(sub["gridBaby"]) + "\n--\n"
              + "\n".join(sub["gridTeen"]) + "\n--\n"
              + "\n".join(sub["gridAdult"]))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def iso_now() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S") + f".{now.microsecond * 10:07d}Z"


def row_key() -> str:
    ticks = UNIX_EPOCH_TICKS + time.time_ns() // 100
    return f"{MAX_TICKS - ticks:019d}-{secrets.token_hex(2)}"


def name_already_queued(name: str) -> bool:
    out = az("storage", "entity", "query", "--table-name", TABLE,
             "--filter", f"PartitionKey eq 'q' and Name eq '{name}'",
             "--select", "RowKey", "-o", "json")
    return len(json.loads(out).get("items", [])) > 0


def file_submission(path: str) -> None:
    sub = json.loads(open(path, encoding="utf-8").read())
    name = sub["name"].strip()
    if name_already_queued(name):
        print(f"SKIP {name} — already has a queue row")
        return

    lore = sub.get("lore", "").strip()
    entity = {
        "PartitionKey": "q",
        "RowKey": row_key(),
        "Type": "species-submission",
        "Status": "pending",
        "SubmitterRef": "",
        "SubmitterName": SUBMITTER_NAME,
        "Title": f"Species: {name}",
        "BodyJson": json.dumps(sub, ensure_ascii=False, separators=(",", ":")),
        "RelatedKey": name.lower(),
        "Name": name,
        "RequestedSeed": sub.get("requestedSeed", ""),
        "GridsHash": grids_hash(sub),
        "LoreHash": hashlib.sha256(lore.encode("utf-8")).hexdigest() if lore else "",
        "Reason": "",
        "CreatedAt": iso_now(),
        "DecidedAt": "",
    }
    az("storage", "entity", "insert", "--table-name", TABLE,
       "--entity", *[f"{k}={v}" for k, v in entity.items()])
    print(f"FILED {name} — pending, row {entity['RowKey']} (approve it in /admin)")


if __name__ == "__main__":
    if not os.environ.get("AZURE_STORAGE_CONNECTION_STRING"):
        raise SystemExit("Set AZURE_STORAGE_CONNECTION_STRING first (see runbook step 1).")
    if len(sys.argv) < 2:
        raise SystemExit("Usage: file-wave.py <submission.json> [...]")
    for f in sys.argv[1:]:
        file_submission(f)
