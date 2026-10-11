#!/usr/bin/env python3
"""dna-scan — no DNA on any page this repository serves.

A DNA GUID is a clone code: anyone who holds one can hatch the same Pal. PRINCIPLES.md (in the game
repository) promises never to publish one, and GitHub Pages serves every file in this repository. So a
drop prints a species' first-egg phrase, never the DNA of its first egg, and this check holds that.

    python3 tools/dna-scan.py                    every served file; exit 1 on any DNA
    python3 tools/dna-scan.py --before-signing   the same, leaving packs/ to the publish
    python3 tools/dna-scan.py --prune            after signing: remove each superseded pack that
                                                 holds a DNA, then scan everything
    python3 tools/dna-scan.py --mint <id> <phrase>   print the first egg a phrase mints (operator use)

What it finds: every string shaped like a GUID (with dashes, braces or none, any case) that the game
would decode as a DNA version 2 code: the version nibble 0xC and the four-byte MAC both match. Every
pack species' first egg is one; so is any other Pal's v2 code. A GUID that is not a Pal's code (a
row key, a random v4 id) fails the MAC and passes. Each finding says whose code it is, and whether it
is that species' first egg.

The served files are what git would commit: tracked files and untracked ones that are not ignored
(publish-drop.sh commits with `git add -A`). Outside a git tree, every file but .git.

Pruning. Packs are content-hashed and never edited, and a superseded one is kept, except that a pack
holding a DNA is removed from the tree once the registry this clone signed no longer names it (it stays
in git history; no client fetches a pack the live registry does not name). A pack the registry names is
never removed: if it holds a DNA the scan fails and the publish must not be pushed.

The decoder and the mint are ports of the game's PalDnaV2 (TryGetSpeciesId, MintFromSeed). Byte order is
.NET's Guid.ToByteArray: the first three groups little-endian. tools/test_drop.py holds the mint equal to
the game's FreezeHarness.
"""

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MAC_TAG = b"cachepal-dna-v2-mac|"
SEED_TAG = "cachepal-seed-v2"
VERSION_NIBBLE = 0xC

# Dashed (Guid "D", inside "B" braces or "P" parens too) or bare 32 hex digits (Guid "N"): every
# spelling the Hatchery's Guid.TryParse takes. Bounded so a 64-digit sha256 is not read as two.
GUID = re.compile(rb"(?<![0-9A-Fa-f])(?:[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}"
                  rb"|[0-9A-Fa-f]{32})(?![0-9A-Fa-f])")


def guid_bytes(text: str) -> bytes:
    h = text.replace("-", "")
    return (bytes.fromhex(h[0:8])[::-1] + bytes.fromhex(h[8:12])[::-1] + bytes.fromhex(h[12:16])[::-1]
            + bytes.fromhex(h[16:32]))


def guid_text(b: bytes) -> str:
    return (f"{b[0:4][::-1].hex()}-{b[4:6][::-1].hex()}-{b[6:8][::-1].hex()}-{b[8:10].hex()}-{b[10:16].hex()}")


def mac(b: bytes) -> bytes:
    return hashlib.sha256(MAC_TAG + b[:12]).digest()[:4]


def species_of(text: str):
    """The species id a DNA v2 code carries, or None when it is not one (PalDnaV2.TryGetSpeciesId)."""
    b = guid_bytes(text)
    if (b[7] >> 4) != VERSION_NIBBLE or b[12:16] != mac(b):
        return None
    return b[4] | (b[5] << 8)


def mint(species_id: int, phrase: str) -> str:
    """The first egg a phrase mints for a species (PalDnaV2.MintFromSeed)."""
    trimmed = phrase.strip()
    if not trimmed:
        raise ValueError("the phrase is empty")
    if not 0 <= species_id <= 0xFFFF:
        raise ValueError("a species id fits in 16 bits")
    e = hashlib.sha256(f"{SEED_TAG}|{species_id}|{trimmed}".encode("utf-8")).digest()[:10]
    b = bytearray(16)
    b[0:4] = e[0:4]
    b[4] = species_id & 0xFF
    b[5] = species_id >> 8
    b[6] = e[4]
    b[7] = (VERSION_NIBBLE << 4) | (e[5] & 0x0F)
    b[8:12] = e[6:10]
    b[12:16] = mac(bytes(b))
    return guid_text(bytes(b))


def registry_payload(root: Path) -> dict | None:
    path = root / "registry.pub.json"
    if not path.exists():
        return None
    env = json.loads(path.read_text(encoding="utf-8"))
    return json.loads(base64.urlsafe_b64decode(env["payload"] + "==="))


def known_species(root: Path) -> dict[int, dict]:
    """Every species this repository knows, by id: its name and, when it has one, its first-egg phrase."""
    known: dict[int, dict] = {}
    payload = registry_payload(root)
    for s in (payload or {}).get("species", []):
        known[s["id"]] = {"name": s.get("name") or s.get("key") or str(s["id"])}
    for f in sorted((root / "species").glob("*.json")) if (root / "species").is_dir() else []:
        try:
            s = json.loads(f.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        if isinstance(s.get("id"), int):
            entry = known.setdefault(s["id"], {"name": s.get("name") or s.get("key")})
            if isinstance(s.get("premiereSeed"), str) and s["premiereSeed"].strip():
                entry["phrase"] = s["premiereSeed"]
    return known


def served_files(root: Path) -> list[Path]:
    r = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                       capture_output=True)
    inside = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if r.returncode == 0 and inside.returncode == 0 and Path(inside.stdout.strip()).resolve() == root.resolve():
        names = [n for n in r.stdout.decode("utf-8").split("\0") if n]
        return sorted(root / n for n in names if (root / n).is_file())
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        out += [Path(dirpath) / f for f in filenames]
    return sorted(out)


def findings_in(path: Path, known: dict[int, dict]) -> list[tuple[int, str]]:
    data = path.read_bytes()
    found = []
    for m in GUID.finditer(data):
        text = m.group().decode("ascii")
        sid = species_of(text)
        if sid is None:
            continue
        line = data.count(b"\n", 0, m.start()) + 1
        who = known.get(sid)
        name = who["name"] if who else f"species {sid}"
        first = bool(who and who.get("phrase")) and mint(sid, who["phrase"]) == guid_text(guid_bytes(text))
        what = f"the first egg of {name} (species {sid})" if first else f"a Pal's DNA ({name}, species {sid})"
        found.append((line, what))
    return found


def prune(root: Path) -> list[str]:
    payload = registry_payload(root)
    if payload is None:
        raise SystemExit("--prune needs registry.pub.json: it removes only what the signed registry no longer names.")
    named = {s["pack"] for s in payload.get("species", [])}
    known = known_species(root)
    removed = []
    for path in sorted((root / "packs").glob("*.json")) if (root / "packs").is_dir() else []:
        rel = path.relative_to(root).as_posix()
        if rel not in named and findings_in(path, known):
            path.unlink()
            removed.append(rel)
    return removed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--before-signing", action="store_true", help="leave packs/ to the publish")
    ap.add_argument("--prune", action="store_true", help="remove superseded packs that hold a DNA, then scan")
    ap.add_argument("--mint", nargs=2, metavar=("ID", "PHRASE"), help="print the first egg a phrase mints")
    args = ap.parse_args()

    if args.mint:
        print(mint(int(args.mint[0]), args.mint[1]))
        return 0

    root = Path(args.root).resolve()
    if args.prune:
        for rel in prune(root):
            print(f"removed {rel}: superseded, and it held a DNA")

    known = known_species(root)
    files = served_files(root)
    bad = 0
    for path in files:
        rel = path.relative_to(root).as_posix()
        if args.before_signing and rel.startswith("packs/"):
            continue
        for line, what in findings_in(path, known):
            print(f"{rel}:{line}: {what}")
            bad += 1
    if bad:
        print(f"\nDNA ON A SERVED PAGE: {bad} code(s). A DNA GUID is a clone code; print the first-egg phrase instead "
              "(PRINCIPLES.md, no public identity built from DNA).")
        return 1
    scope = " (packs/ left to the publish)" if args.before_signing else ""
    print(f"no DNA in {len(files)} served files{scope}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
