#!/usr/bin/env python3
"""drop — publish a reviewed drop, from the queue to the stamped rows, with one command.

    python3 tools/drop.py --dry-run             rehearse in a throwaway copy; writes nothing anywhere
    python3 tools/drop.py --dry-run --fixture   the same, with a made-up version 2 row instead of the queue
    python3 tools/drop.py                       publish (it rehearses first, and stops if that is not green)

Options: --drop-tag 2026-W41 (default: this ISO week), --cachepal-root <game repo> (default
$CACHEPAL_ROOT, else the clone beside this one), --overlays <dir> (only for a version 1 row),
--rows <file> (with --dry-run: the approved pool from a file), --keep (with --dry-run: keep the copy).

In order:
  1. The key. Its public half must be the game's ContentSyncService.PublicKeys[0], and the live
     registry's signature must verify under that half. The key is never printed.
  2. The clone. On main, clean, the same commit as GitHub's main, and its registry.pub.json the
     same bytes as the live one. A real run stops on any of these; a dry run lists them.
  3. The rehearsal, always, in a throwaway clone whose origin is a throwaway bare repository, signed
     with a key made for the run (so no rehearsal makes a signature a player's game would accept):
     the approved, unpublished rows of BarnQueue (read through az, as build-drop.py reads them) are
     built by build-drop.py; palpack validates; the species count must be the live count plus the
     new species; no DNA may be in a served file; the build is committed and pushed; publish-drop.sh
     signs, writes the drop into DROPS.md, removes superseded packs that held a DNA, scans again,
     commits and pushes; the signed registry is read back and its signature checked.
  4. A real run then does step 3 in this clone, with the real key and the real origin, and stops
     before anything is pushed if the queue gave a different set of rows than the rehearsal did.
  5. It stamps PublishedAt (and the Reason the maker reads) on exactly the rows it shipped, and
     reads them back. A dry run prints the stamps it would make.
  6. The gallery hook, mark_in_game_in_gallery: if the Barn's gallery table exists, the creations
     this drop shipped are marked in the game. Nothing depends on it.
  7. It prints what it published.

Nothing approved and unpublished in the queue means no drop: it says so and stops. Approval is a
person's review in the Barn's /admin, never this tool's.

Its checks: python3 tools/test_drop.py (throwaway copies, a localhost registry, a key made per run).
"""

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIVE_URL = os.environ.get("PALPACK_REGISTRY_URL") or "https://the3dcoder.github.io/CachePalContent/registry.pub.json"
KEY_FILE = Path(os.environ.get("PALPACK_KEY_FILE") or Path.home() / ".cachepal" / "signing.key")
STORAGE_ACCOUNT, RESOURCE_GROUP = "cachepalbarn", "cachepal"
QUEUE_TABLE, GALLERY_TABLE = "BarnQueue", "BarnGallery"

# A made-up version 2 row, shaped as the Barn api stores one (SpeciesSubmission.ToJson), for
# `--dry-run --fixture`. It is built only in a throwaway copy and can never be published.
_GRID = ["................", "................", "....OOOOOOOO....", "...OBBBBBBBBO...", "..OBBWEBBWEBBO..",
         "..OBBEEBBEEBBO..", "..OBBBBBBBBBBO..", "..OBBBMMBBBBBO..", "..OBCBBBBBCBBO..", "..OBBSSSSSSBBO..",
         "..OABSSSSSSBAO..", "...OBBSSSSBBO...", "....OBBBBBBO....", ".....OOOOOO.....", "................",
         "................"]
_STEP = _GRID[:13] + ["....OO....OO...."] + _GRID[14:]
FIXTURE_BODY = {
    "version": 2, "name": "Rehearsal Fern", "element": "Bloom",
    "lore": "A made-up Pal that exists only to rehearse a drop.",
    "biasPower": 1, "biasMischief": 0, "biasStealth": 0, "biasResilience": -1, "biasLuck": 0, "biasSignal": 0,
    "suggestedWeight": 60, "requestedSeed": "a rehearsal, never a drop",
    "gridBaby": _GRID, "gridTeen": _GRID, "gridAdult": _GRID, "gridElder": [],
    "gridAdultB": _STEP, "overlays": [],
    "baseColor": "#63ab3f", "shinyColor": "#f0b541", "bodyArchetype": "quad", "hungryFor": "berry mix",
    "needDecayBias": [1.2, 1, 0.9, 1, 0.9], "babyDescription": "A sprout with ideas.",
    "teenDescription": "Taller now, and twice as nosy.", "adultDescription": "A friend with bark and a good ear.",
}
FIXTURE_ROWS = [{"PartitionKey": "q", "RowKey": "rehearsal-fixture", "Type": "species-submission",
                 "Status": "approved", "SubmitterName": "rehearsal",
                 "BodyJson": json.dumps(FIXTURE_BODY, separators=(",", ":"))}]

# Ed25519 in node (python's standard library has none). Key material travels in the environment,
# never in argv, and only public halves are printed.
NODE_PUBLIC_HALF = """
const {createPrivateKey, createPublicKey} = require('crypto');
const der = Buffer.concat([Buffer.from('302e020100300506032b657004220420', 'hex'), Buffer.from(process.env.DROP_KEY, 'base64url')]);
console.log(createPublicKey(createPrivateKey({key: der, format: 'der', type: 'pkcs8'})).export({format: 'jwk'}).x);
"""
NODE_THROWAWAY = """
const k = require('crypto').generateKeyPairSync('ed25519');
console.log(JSON.stringify({d: k.privateKey.export({format: 'jwk'}).d, x: k.publicKey.export({format: 'jwk'}).x}));
"""
NODE_VERIFY = """
const {createPublicKey, verify} = require('crypto');
const env = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const pub = createPublicKey({key: {kty: 'OKP', crv: 'Ed25519', x: process.env.DROP_PUB}, format: 'jwk'});
process.exit(verify(null, Buffer.from(env.payload, 'base64url'), pub, Buffer.from(env.signature, 'base64url')) ? 0 : 1);
"""


class Stop(Exception):
    """A refusal: the message says why, and what state things were left in."""


def say(msg: str) -> None:
    print(f"▸ {msg}", flush=True)


def note(msg: str) -> None:
    print(f"  {msg}", flush=True)


def run(args, cwd=None, env=None, check=True, capture=True, stdin=None) -> subprocess.CompletedProcess:
    r = subprocess.run(args, cwd=cwd, env={**os.environ, **(env or {})}, text=True, input=stdin,
                       capture_output=capture)
    if check and r.returncode != 0:
        detail = ((r.stdout or "") + (r.stderr or "")).strip() if capture else ""
        raise Stop(f"{' '.join(str(a) for a in args[:4])}… exited {r.returncode}" + (f":\n{detail}" if detail else ""))
    return r


def git(tree: Path, *args, check=True) -> str:
    return run(["git", "-C", str(tree), *args], check=check).stdout.strip()


def payload_of(envelope_text: str) -> dict:
    return json.loads(base64.urlsafe_b64decode(json.loads(envelope_text)["payload"] + "==="))


def fetch_live() -> str:
    with urllib.request.urlopen(LIVE_URL, timeout=30) as r:
        return r.read().decode("utf-8")


# ---- 1. the key ---------------------------------------------------------------------------------

def pinned_public_key(cachepal_root: Path) -> str:
    src = cachepal_root / "src" / "CachePal.Web" / "Services" / "ContentSyncService.cs"
    if not src.exists():
        raise Stop(f"No {src}: --cachepal-root (or CACHEPAL_ROOT) must name the game repository.")
    m = re.search(r'PublicKeys\s*=\s*\[\s*"([A-Za-z0-9_-]{43})"', src.read_text(encoding="utf-8"))
    if not m:
        raise Stop(f"Could not read PublicKeys[0] from {src}.")
    return m.group(1)


def signing_key() -> str:
    if os.environ.get("PALPACK_KEY"):
        return os.environ["PALPACK_KEY"].strip()
    if not KEY_FILE.exists():
        raise Stop(f"No signing key: PALPACK_KEY is not set and there is no {KEY_FILE}. Place it from the vault "
                   "(the game repo's docs/runbooks/CREDENTIALS.md).")
    mode = KEY_FILE.stat().st_mode & 0o777
    if mode & 0o077:
        raise Stop(f"{KEY_FILE} is mode {mode:o}: chmod 600 it first.")
    return KEY_FILE.read_text().strip()


def public_half(private: str) -> str:
    return run(["node", "-e", NODE_PUBLIC_HALF], env={"DROP_KEY": private}).stdout.strip()


def verifies(envelope_text: str, public: str) -> bool:
    return run(["node", "-e", NODE_VERIFY], env={"DROP_PUB": public}, stdin=envelope_text, check=False).returncode == 0


def check_key(cachepal_root: Path, live_text: str) -> str:
    pinned = pinned_public_key(cachepal_root)
    if public_half(signing_key()) != pinned:
        raise Stop("The signing key's public half is not ContentSyncService.PublicKeys[0]: a drop signed with it "
                   "would be refused by every game. Fetch the right key from the vault.")
    say(f"key: its public half is ContentSyncService.PublicKeys[0] ({pinned[:8]}…)")
    if not verifies(live_text, pinned):
        raise Stop("The live registry's signature does not verify under PublicKeys[0]. Find out why before signing anything.")
    note(f"the live registry (generation {payload_of(live_text)['generation']}) verifies under it")
    return pinned


# ---- 2. the clone ---------------------------------------------------------------------------------

def clone_blockers(live_text: str) -> list[str]:
    """What would stop a real run from this clone. Empty when it may publish."""
    blockers = []
    branch = git(ROOT, "rev-parse", "--abbrev-ref", "HEAD")
    if branch != "main":
        blockers.append(f"the clone is on '{branch}': drops publish from main")
    if git(ROOT, "status", "--porcelain"):
        blockers.append("the clone has uncommitted changes: what is signed is a commit")
    remote = git(ROOT, "ls-remote", "origin", "refs/heads/main", check=False).split()
    if not remote:
        blockers.append("could not read origin's main")
    elif remote[0] != git(ROOT, "rev-parse", "HEAD"):
        blockers.append(f"HEAD is not origin's main ({remote[0][:8]}): pull or push first")
    if (ROOT / "registry.pub.json").read_text(encoding="utf-8") != live_text:
        blockers.append("this clone's registry.pub.json is not the live one: pull first (a stale clone unpublishes "
                        "whatever the newer generations added)")
    return blockers


# ---- 3. one drop in one tree ------------------------------------------------------------------------

def storage_env() -> dict:
    if os.environ.get("AZURE_STORAGE_CONNECTION_STRING"):
        return {}
    conn = run(["az", "storage", "account", "show-connection-string", "-n", STORAGE_ACCOUNT, "-g", RESOURCE_GROUP,
                "--query", "connectionString", "-o", "tsv"]).stdout.strip()
    if not conn:
        raise Stop("Could not read the Barn's storage connection string through az (az login first).")
    os.environ["AZURE_STORAGE_CONNECTION_STRING"] = conn  # this process and its children only
    return {}


def notes_for(manifest: list[dict], tag: str, today: str) -> str:
    """This drop's section of DROPS.md. First-egg phrases only: never a DNA."""
    lines = [f"## Generation @GENERATION@ — drop {tag} ({today})", ""]
    new = [m for m in manifest if m["type"] == "species-submission"]
    if new:
        count = ["One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
        said = count[len(new) - 1] if len(new) <= len(count) else str(len(new))
        lines.append(f"{said} new species, reviewed in the Barn's /admin and published by `tools/drop.py`.")
        lines.append("")
        for m in new:
            element = f", {m['element']}" if m.get("element") else ""
            lines.append(f"**{m['name']}** (species {m['id']}{element}), drawn by {m['by']} — first-egg phrase: "
                         f"\"{m['phrase']}\"")
            if m.get("lore"):
                lines.append(f"_{m['lore']}_")
            lines.append("")
    changes = [m for m in manifest if m["type"] != "species-submission"]
    if changes:
        lines.append("Also in this drop:")
        lines.append("")
        for m in changes:
            who = f", from {m['by']}" if m.get("by") else ""
            lines.append(f"- **{m['name']}** (species {m['id']}): {m['change']}{who}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def one_drop(tree: Path, work: Path, args, live: dict, env: dict, rehearsal_manifest=None):
    """Build, validate, scan, commit, push and sign one drop in `tree`. Returns the manifest, or None
    when there is nothing approved and unpublished. Raises Stop on any refusal."""
    manifest_path = work / "manifest.json"
    cmd = [sys.executable, str(tree / "tools" / "build-drop.py"), "--cachepal-root", str(args.cachepal_root),
           "--drop-tag", args.drop_tag, "--manifest", str(manifest_path)]
    if args.overlays:
        cmd += ["--overlays", str(Path(args.overlays).resolve())]
    if args.rows_file:
        cmd += ["--rows", str(args.rows_file)]
    build = run(cmd, cwd=tree, env=env, check=False)
    for line in build.stdout.splitlines():
        if line.startswith(("WROTE", "REVISED", "EDITED", "SKIP", "WARN")):
            note(line)
    if build.returncode != 0:
        raise Stop(f"build-drop refused:\n{(build.stdout + build.stderr).strip()}")
    manifest = json.loads(manifest_path.read_text())
    if not manifest:
        git(tree, "checkout", "-q", "--", "species")
        return None
    if rehearsal_manifest is not None:
        def shape(ms):
            return [(m["rowKey"], m["type"], m.get("id"), m.get("key"), m.get("name"), m.get("phrase")) for m in ms]
        if shape(manifest) != shape(rehearsal_manifest):
            git(tree, "checkout", "-q", "--", "species")
            git(tree, "clean", "-fdq", "--", "species")
            raise Stop("The queue gave a different set of rows than the rehearsal did (a review landed in between). "
                       "Nothing was committed; run the drop again.")

    valid = run(["node", "tools/palpack.mjs", "validate"], cwd=tree, env=env, check=False)
    if valid.returncode != 0:
        raise Stop(f"palpack refused what build-drop wrote:\n{(valid.stdout + valid.stderr).strip()}")
    count = int(re.search(r"all valid — (\d+) species", valid.stdout).group(1))
    new = [m for m in manifest if m["type"] == "species-submission"]
    expected = len(live["species"]) + len(new)
    if count != expected:
        raise Stop(f"The tree holds {count} species; the live registry's {len(live['species'])} and this drop's "
                   f"{len(new)} new ones make {expected}. Refusing (B350: the count is the check).")
    note(f"palpack: {count} species valid, the live {len(live['species'])} and {len(new)} new")

    scan = run([sys.executable, "tools/dna-scan.py", "--before-signing"], cwd=tree, check=False)
    if scan.returncode != 0:
        raise Stop(f"A Pal's DNA is in a file this site serves:\n{scan.stdout.strip()}")

    notes_path = work / "notes.md"
    notes_path.write_text(notes_for(manifest, args.drop_tag, datetime.now(timezone.utc).strftime("%Y-%m-%d")))

    keys = sorted({m["key"] for m in manifest if m.get("key")})
    git(tree, "add", "--", *[f"species/{k}.json" for k in keys])
    stray = git(tree, "status", "--porcelain", "--untracked-files=all")
    if any(not line.startswith(("M  ", "A  ")) for line in stray.splitlines()):
        raise Stop(f"build-drop left files this drop does not name:\n{stray}")
    names = ", ".join(m["name"] for m in manifest)
    git(tree, "commit", "-q", "-m", f"drops: build {args.drop_tag} — {names}")
    git(tree, "push", "-q", "origin", "main")
    build_commit = git(tree, "rev-parse", "--short", "HEAD")
    note(f"build commit {build_commit} pushed: {names}")

    publish_env = {**env, "PUBLISH_DROP_NOTES": str(notes_path)}
    pub = run(["./tools/publish-drop.sh", str(expected)], cwd=tree, env=publish_env, check=False, capture=False)
    if pub.returncode != 0:
        raise Stop(f"publish-drop.sh stopped (above). The build commit {build_commit} is on origin's main and no "
                   f"queue row is stamped. Fix the cause, then revert that commit (git revert {build_commit} && git "
                   "push) and run the drop again, or finish by hand: PUBLISH_DROP_NOTES="
                   f"{notes_path} ./tools/publish-drop.sh {expected}, then the stamps in {manifest_path}.")
    return manifest


def read_back(tree: Path, live: dict, manifest: list[dict], public: str) -> dict:
    text = (tree / "registry.pub.json").read_text(encoding="utf-8")
    signed = payload_of(text)
    if signed["generation"] != live["generation"] + 1:
        raise Stop(f"The signed registry is generation {signed['generation']}; it should be {live['generation'] + 1}.")
    if not verifies(text, public):
        raise Stop("The signed registry does not verify under the key it was meant to be signed with.")
    by_id = {s["id"]: s for s in signed["species"]}
    for m in manifest:
        if m["type"] == "species-submission" and by_id.get(m["id"], {}).get("name") != m["name"]:
            raise Stop(f"{m['name']} (species {m['id']}) is not in the signed registry.")
    scan = run([sys.executable, "tools/dna-scan.py"], cwd=tree, check=False)
    if scan.returncode != 0:
        raise Stop(f"A Pal's DNA is served after the publish:\n{scan.stdout.strip()}")
    note(f"read back: generation {signed['generation']}, {len(signed['species'])} species, the signature verifies, "
         f"and {scan.stdout.strip()}")
    return signed


# ---- 5 and 6. the queue and the gallery ---------------------------------------------------------------

def stamp_rows(manifest: list[dict], dry: bool) -> None:
    at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for m in manifest:
        fields = [f"RowKey={m['rowKey']}", f"PublishedAt={at}"] + ([f"Reason={m['reason']}"] if m.get("reason") else [])
        if dry:
            note(f"would stamp {QUEUE_TABLE} row {m['rowKey']} ({m['name']}): PublishedAt"
                 + (f", Reason \"{m['reason']}\"" if m.get("reason") else ""))
            continue
        run(["az", "storage", "entity", "merge", "--table-name", QUEUE_TABLE, "--entity", "PartitionKey=q", *fields, "-o", "none"])
    if dry:
        return
    for m in manifest:
        got = run(["az", "storage", "entity", "show", "--table-name", QUEUE_TABLE, "--partition-key", "q",
                   "--row-key", m["rowKey"], "--select", "PublishedAt", "-o", "json"]).stdout
        if not json.loads(got).get("PublishedAt"):
            raise Stop(f"Row {m['rowKey']} ({m['name']}) reads back with no PublishedAt.")
    note(f"stamped PublishedAt on {len(manifest)} queue row(s), and read each back")


def mark_in_game_in_gallery(manifest: list[dict], dry: bool) -> None:
    """THE GALLERY HOOK. The Barn's gallery (ROADMAP track 1 step 4, lane feature/gallery) keeps a row per
    accepted creation in the table BarnGallery, partition 'g', with the queue row it came from in QueueId,
    and shows a creation as in the game once InGame is true. The gallery marks that itself when it finds
    the art in the published registry; this hook marks it at publish time as well. It never fails a drop:
    no table means nothing to mark, and an error is a warning."""
    shipped = [m for m in manifest if m["type"] == "species-submission"]
    if not shipped:
        return
    if dry:
        note(f"gallery hook: would mark {', '.join(m['name'] for m in shipped)} in the game, if {GALLERY_TABLE} exists")
        return
    try:
        exists = json.loads(run(["az", "storage", "table", "exists", "--name", GALLERY_TABLE, "-o", "json"]).stdout)
        if not exists.get("exists"):
            note(f"gallery hook: no {GALLERY_TABLE} table yet, so nothing to mark")
            return
        at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for m in shipped:
            rows = json.loads(run(["az", "storage", "entity", "query", "--table-name", GALLERY_TABLE, "--filter",
                                   f"PartitionKey eq 'g' and QueueId eq '{m['rowKey']}'", "--select", "RowKey",
                                   "-o", "json"]).stdout).get("items", [])
            for g in rows:
                run(["az", "storage", "entity", "merge", "--table-name", GALLERY_TABLE, "--entity", "PartitionKey=g",
                     f"RowKey={g['RowKey']}", "InGame=true", "InGame@odata.type=Edm.Boolean", f"SpeciesId={m['id']}",
                     "SpeciesId@odata.type=Edm.Int32", f"InGameAt={at}", "-o", "none"])
                note(f"gallery hook: {m['name']} ({g['RowKey']}) marked in the game")
    except (Stop, ValueError) as e:
        print(f"! gallery hook: {e} (the drop is published; the gallery marks it itself)", flush=True)


# ---- the run ----------------------------------------------------------------------------------------------

def rehearse(args, live: dict, work: Path):
    """Step 3 in a throwaway clone of HEAD, with a throwaway origin and a throwaway key."""
    tree, origin = work / "content", work / "origin.git"
    head = git(ROOT, "rev-parse", "HEAD")
    run(["git", "clone", "-q", "--no-local", str(ROOT), str(tree)])
    git(tree, "checkout", "-q", "-B", "main", head)
    run(["git", "clone", "-q", "--bare", str(tree), str(origin)])
    git(tree, "remote", "set-url", "origin", str(origin))
    git(tree, "fetch", "-q", "origin")
    git(tree, "branch", "-q", "--set-upstream-to=origin/main", "main")
    for k, fallback in (("user.name", "Cache Pal drop rehearsal"), ("user.email", "rehearsal@localhost")):
        git(tree, "config", k, git(ROOT, "config", k, check=False) or fallback)
    keys = json.loads(run(["node", "-e", NODE_THROWAWAY]).stdout)
    env = {"PALPACK_KEY": keys["d"], "PUBLISH_DROP_REHEARSAL": "1", "CACHEPAL_GAME_REPO": str(args.cachepal_root)}
    say(f"rehearsal: a throwaway clone of {head[:8]}, a throwaway origin and a key made for the run, in {work}")
    manifest = one_drop(tree, work, args, live, env)
    if manifest is None:
        return None, None
    signed = read_back(tree, live, manifest, keys["x"])
    return manifest, signed


def summary(manifest: list[dict], signed: dict, tag: str, rehearsal: bool) -> None:
    verb = "would publish" if rehearsal else "published"
    print(f"\n{'Rehearsal: this drop ' if rehearsal else ''}{verb} generation {signed['generation']} (drop {tag}): "
          f"{len(signed['species'])} species.", flush=True)
    for m in manifest:
        if m["type"] == "species-submission":
            print(f"  new: {m['name']} (species {m['id']}, {m.get('element') or 'no element'}), drawn by {m['by']}. "
                  f"First-egg phrase: \"{m['phrase']}\".", flush=True)
        else:
            print(f"  {m['type']}: {m['name']} (species {m['id']}): {m['change']}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Publish a reviewed drop with one command.")
    ap.add_argument("--dry-run", action="store_true", help="rehearse in a throwaway copy; write nothing anywhere")
    ap.add_argument("--fixture", action="store_true", help="with --dry-run: a made-up version 2 row, not the queue")
    ap.add_argument("--rows", help="with --dry-run: the approved pool from this file, not the queue")
    ap.add_argument("--keep", action="store_true", help="with --dry-run: keep the throwaway copy")
    ap.add_argument("--drop-tag", default=datetime.now(timezone.utc).strftime("%G-W%V"))
    ap.add_argument("--cachepal-root", default=os.environ.get("CACHEPAL_ROOT") or str(ROOT.parent / "CachePal"))
    ap.add_argument("--overlays", help="a directory of <key>.overlay.json files, for version 1 rows")
    args = ap.parse_args()
    if (args.fixture or args.rows or args.keep) and not args.dry_run:
        ap.error("--fixture, --rows and --keep rehearse only: add --dry-run")
    if args.fixture and args.rows:
        ap.error("--fixture or --rows, not both")
    args.cachepal_root = Path(args.cachepal_root).resolve()

    work = Path(tempfile.mkdtemp(prefix="drop-"))
    args.rows_file = None
    if args.fixture:
        args.rows_file = work / "fixture-rows.json"
        args.rows_file.write_text(json.dumps(FIXTURE_ROWS))
    elif args.rows:
        args.rows_file = Path(args.rows).resolve()
    keep = args.keep
    real_started = False
    try:
        live_text = fetch_live()
        live = payload_of(live_text)
        say(f"live: generation {live['generation']}, {len(live['species'])} species ({LIVE_URL})")
        check_key(args.cachepal_root, live_text)
        blockers = clone_blockers(live_text)
        if blockers and not args.dry_run:
            raise Stop("This clone cannot publish:\n  " + "\n  ".join(blockers))
        if args.rows_file is None:
            storage_env()

        manifest, signed = rehearse(args, live, work / "rehearsal")
        if manifest is None:
            print("\nNothing approved and unpublished in the queue: no drop. (Approval is a person's review in "
                  "the Barn's /admin.)", flush=True)
            if blockers:
                print("\nA real run from this clone would stop first:\n  " + "\n  ".join(blockers), flush=True)
            return 0
        say("rehearsal green")

        if args.dry_run:
            stamp_rows(manifest, dry=True)
            mark_in_game_in_gallery(manifest, dry=True)
            summary(manifest, signed, args.drop_tag, rehearsal=True)
            if blockers:
                print("\nA real run from this clone would stop first:\n  " + "\n  ".join(blockers), flush=True)
            print("\nDry run: nothing was pushed to GitHub, signed with the real key, or written to a table.", flush=True)
            return 0

        say("the drop, for real")
        real_started = True
        (work / "real").mkdir()
        real = one_drop(ROOT, work / "real", args, live, {"CACHEPAL_GAME_REPO": str(args.cachepal_root)},
                        rehearsal_manifest=manifest)
        if real is None:
            raise Stop("The queue had nothing approved and unpublished by the time of the real run. Nothing was written.")
        signed = read_back(ROOT, live, real, pinned_public_key(args.cachepal_root))
        try:
            stamp_rows(real, dry=False)
        except Stop as e:
            raise Stop(f"Generation {signed['generation']} is published, but the queue rows are not all stamped: {e}\n"
                       f"Stamp each row in {work / 'real' / 'manifest.json'} by hand: az storage entity merge "
                       "--table-name BarnQueue --entity PartitionKey=q RowKey=<rowKey> PublishedAt=<now, ISO 8601 Z> "
                       "'Reason=<its reason>'. Do not run the drop again.")
        mark_in_game_in_gallery(real, dry=False)
        try:
            now = payload_of(fetch_live())
            note(f"live now: generation {now['generation']}" + ("" if now["generation"] == signed["generation"]
                 else f" (the CDN still serves the old one; {signed['generation']} is pushed)"))
        except OSError:
            pass
        summary(real, signed, args.drop_tag, rehearsal=False)
        return 0
    except Stop as e:
        print(f"\n✘ {e}", file=sys.stderr, flush=True)
        if real_started:
            keep = True  # the manifest and notes the messages above name
            print(f"  (this drop's manifest and notes are kept in {work / 'real'})", file=sys.stderr, flush=True)
        return 1
    finally:
        if not keep:
            shutil.rmtree(work, ignore_errors=True)
        elif args.keep:
            print(f"kept: {work}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
