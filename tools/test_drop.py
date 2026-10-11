#!/usr/bin/env python3
"""Checks for the drop path: tools/dna-scan.py, and tools/drop.py's rehearsal.

    python3 tools/test_drop.py            (or: python3 -m unittest tools/test_drop.py)

Everything runs in throwaway copies. Nothing here touches this clone, Azure, the signing key or the
live channel: the "live" registry is a localhost server, the key is made for the run, and the queue
is a fixture file.

No DNA is written in this file. A DNA GUID is a clone code (PRINCIPLES.md: no public identity built
from DNA), and this file is served by GitHub Pages like every other file here, so the checks mint the
codes they need at run time.
"""

import base64
import hashlib
import http.server
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
GAME = os.environ.get("CACHEPAL_GAME_REPO") or str(HERE.parent / "CachePal")
SCAN = HERE / "tools" / "dna-scan.py"


def run(args, cwd=None, env=None, check=False):
    r = subprocess.run(args, cwd=cwd, env={**os.environ, **(env or {})}, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise AssertionError(f"{args} exited {r.returncode}:\n{r.stdout}\n{r.stderr}")
    return r


def scan(root, *flags):
    return run([sys.executable, str(SCAN), "--root", str(root), *flags])


def mint(species_id: int, seed: str) -> str:
    r = run([sys.executable, str(SCAN), "--mint", str(species_id), seed], check=True)
    return r.stdout.strip()


def copy_repo(dest: Path) -> Path:
    """A throwaway git clone of this repository with its working tree on top, committed there on a
    branch called main: the checks hold what is being written, committed here or not."""
    run(["git", "clone", "-q", "--no-local", str(HERE), str(dest)], check=True)
    run(["git", "-C", str(dest), "checkout", "-q", "-B", "main"], check=True)
    listed = run(["git", "-C", str(HERE), "ls-files", "-z", "--cached", "--others", "--exclude-standard"], check=True)
    keep = {n for n in listed.stdout.split("\0") if n}
    for name in keep:
        src = HERE / name
        if src.is_file():
            (dest / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest / name)
    for name in run(["git", "-C", str(dest), "ls-files", "-z"], check=True).stdout.split("\0"):
        if name and name not in keep:
            (dest / name).unlink(missing_ok=True)
    run(["git", "-C", str(dest), "add", "-A"], check=True)
    if run(["git", "-C", str(dest), "status", "--porcelain"]).stdout.strip():
        run(["git", "-C", str(dest), "-c", "user.name=check", "-c", "user.email=check@localhost",
             "commit", "-q", "-m", "the working tree under test"], check=True)
    return dest


def registry_payload(root: Path) -> dict:
    env = json.loads((root / "registry.pub.json").read_text())
    return json.loads(base64.urlsafe_b64decode(env["payload"] + "==="))


class DnaScan(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="dna-scan-check-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.root = self.tmp / "content"
        self.root.mkdir()
        (self.root / "species").mkdir()
        (self.root / "packs").mkdir()
        (self.root / "species" / "mossbit.json").write_text(json.dumps(
            {"id": 42, "key": "mossbit", "name": "Mossbit", "premiereSeed": "under the stone"}))
        (self.root / "DROPS.md").write_text("# Content drops\n\nMossbit, first-egg phrase: “under the stone”.\n")

    def test_a_clean_tree_passes(self):
        r = scan(self.root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_a_premiere_printed_in_the_drop_notes_fails_and_is_named(self):
        dna = mint(42, "under the stone")
        with open(self.root / "DROPS.md", "a") as f:
            f.write(f"\nPremiere code: `{dna}`\n")
        r = scan(self.root)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("DROPS.md:5", r.stdout)
        self.assertIn("Mossbit", r.stdout)
        self.assertIn("first egg", r.stdout)

    def test_any_pals_dna_fails_not_only_a_premiere_and_in_every_spelling(self):
        for i, spelled in enumerate((lambda g: g.upper(), lambda g: g.replace("-", ""), lambda g: "{" + g + "}")):
            dna = mint(42, f"some other egg {i}")
            (self.root / "note.txt").write_text(f"look: {spelled(dna)}\n")
            r = scan(self.root)
            self.assertEqual(r.returncode, 1, f"spelling {i} was not caught:\n{r.stdout}{r.stderr}")
            self.assertIn("note.txt:1", r.stdout)

    def test_a_guid_that_is_not_a_pals_dna_passes(self):
        (self.root / "note.txt").write_text("row 6f1d2c3b-9a8e-4f7d-b6c5-a4b3c2d1e0f9 and sha "
                                            + hashlib.sha256(b"x").hexdigest() + "\n")
        r = scan(self.root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_before_signing_leaves_the_packs_to_the_publish(self):
        (self.root / "packs" / "pack-42-mossbit.aaaaaaaa.json").write_text(json.dumps({"premiereDna": mint(42, "under the stone")}))
        self.assertEqual(scan(self.root).returncode, 1)
        r = scan(self.root, "--before-signing")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_prune_removes_only_superseded_packs_that_hold_a_dna(self):
        named = "pack-42-mossbit.bbbbbbbb.json"
        payload = {"generation": 2, "species": [{"id": 42, "key": "mossbit", "pack": f"packs/{named}"}]}
        (self.root / "registry.pub.json").write_text(json.dumps(
            {"payload": base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("="), "signature": "x"}))
        (self.root / "packs" / named).write_text(json.dumps({"premiereSeed": "under the stone"}))
        (self.root / "packs" / "pack-42-mossbit.aaaaaaaa.json").write_text(json.dumps({"premiereDna": mint(42, "under the stone")}))
        (self.root / "packs" / "pack-42-mossbit.cccccccc.json").write_text(json.dumps({"premiereSeed": "older, no code"}))
        r = scan(self.root, "--prune")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        left = sorted(p.name for p in (self.root / "packs").iterdir())
        self.assertEqual(left, ["pack-42-mossbit.bbbbbbbb.json", "pack-42-mossbit.cccccccc.json"])

    def test_prune_never_removes_a_pack_the_signed_registry_names(self):
        named = "pack-42-mossbit.bbbbbbbb.json"
        payload = {"generation": 2, "species": [{"id": 42, "key": "mossbit", "pack": f"packs/{named}"}]}
        (self.root / "registry.pub.json").write_text(json.dumps(
            {"payload": base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("="), "signature": "x"}))
        (self.root / "packs" / named).write_text(json.dumps({"premiereDna": mint(42, "under the stone")}))
        r = scan(self.root, "--prune")
        self.assertEqual(r.returncode, 1, "a named pack holding a DNA must stay, and fail the check")
        self.assertTrue((self.root / "packs" / named).exists())

    @unittest.skipUnless(shutil.which("dotnet") and Path(GAME, "tools", "FreezeHarness").is_dir(),
                         "needs the game repo's FreezeHarness and dotnet")
    def test_the_mint_matches_the_games_own(self):
        """The scanner's mint is a port of PalDnaV2.MintFromSeed; FreezeHarness is the original."""
        for species_id, seed in ((900, "dna-scan parity"), (65535, "  trimmed both ends  "), (14, "été — première")):
            r = run(["dotnet", "run", "--project", str(Path(GAME, "tools", "FreezeHarness")), "--", "mint", str(species_id), seed],
                    check=True)
            theirs = r.stdout.strip().splitlines()[-1].split("|")[0]
            self.assertEqual(mint(species_id, seed), theirs, f"{species_id} {seed!r}")


class PalpackRefusesDna(unittest.TestCase):
    """A pack is served to every device, so palpack refuses a species source that carries a DNA."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="palpack-dna-check-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.repo = copy_repo(self.tmp / "content")

    def validate(self):
        return run(["node", "tools/palpack.mjs", "validate"], cwd=self.repo, env={"CACHEPAL_GAME_REPO": GAME})

    def test_the_species_sources_carry_no_dna_and_validate(self):
        r = self.validate()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_a_premiere_dna_in_a_species_source_is_refused(self):
        path = self.repo / "species" / "glowtail.json"
        s = json.loads(path.read_text())
        s["premiereDna"] = mint(s["id"], s["premiereSeed"])
        path.write_text(json.dumps(s, indent=2))
        r = self.validate()
        self.assertNotEqual(r.returncode, 0, "palpack signed a clone code into a served pack")
        self.assertIn("premiereDna", r.stderr)
        self.assertIn("clone code", r.stderr)


NODE_KEYS = """
const k = require('crypto').generateKeyPairSync('ed25519');
console.log(JSON.stringify({d: k.privateKey.export({format: 'jwk'}).d, x: k.publicKey.export({format: 'jwk'}).x}));
"""
NODE_SIGN = """
const {createPrivateKey, sign} = require('crypto');
const fs = require('fs');
const path = process.argv[1];
const env = JSON.parse(fs.readFileSync(path, 'utf8'));
const der = Buffer.concat([Buffer.from('302e020100300506032b657004220420', 'hex'), Buffer.from(process.env.KEY, 'base64url')]);
env.signature = sign(null, Buffer.from(env.payload, 'base64url'), createPrivateKey({key: der, format: 'der', type: 'pkcs8'})).toString('base64url');
fs.writeFileSync(path, JSON.stringify(env, null, 2));
"""
DOTNET_STUB = "#!/usr/bin/env python3\nprint('11111111-2222-4333-8444-555555555555|0|stub')\n"


class Rehearsal(unittest.TestCase):
    """tools/drop.py --dry-run, end to end in a throwaway world: a clone of this repository whose origin
    is a throwaway bare repository, a game root holding a key made for the run, and a localhost registry
    signed with that key."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="drop-check-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.repo = copy_repo(self.tmp / "content")
        bare = self.tmp / "origin.git"
        run(["git", "clone", "-q", "--bare", str(self.repo), str(bare)], check=True)
        run(["git", "-C", str(self.repo), "remote", "set-url", "origin", str(bare)], check=True)
        run(["git", "-C", str(self.repo), "fetch", "-q", "origin"], check=True)
        run(["git", "-C", str(self.repo), "branch", "-q", "--set-upstream-to=origin/main", "main"], check=True)

        self.keys = json.loads(run(["node", "-e", NODE_KEYS], check=True).stdout)
        run(["node", "-e", NODE_SIGN, str(self.repo / "registry.pub.json")], env={"KEY": self.keys["d"]}, check=True)
        run(["git", "-C", str(self.repo), "-c", "user.name=check", "-c", "user.email=check@localhost",
             "commit", "-qam", "signed with the run's key"], check=True)
        run(["git", "-C", str(self.repo), "push", "-q", "origin", "main"], check=True)

        self.game = self.tmp / "game"
        self.pin(self.keys["x"])
        (self.game / "tools" / "FreezeHarness").mkdir(parents=True)
        shutil.copy2(Path(GAME, "tools", "palpack-overlays.mjs"), self.game / "tools" / "palpack-overlays.mjs")
        self.key_file = self.tmp / "signing.key"
        self.key_file.write_text(self.keys["d"])
        self.key_file.chmod(0o600)

        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        (self.bin / "dotnet").write_text(DOTNET_STUB)
        (self.bin / "dotnet").chmod(0o755)

        live = self.tmp / "live"
        live.mkdir()
        shutil.copy2(self.repo / "registry.pub.json", live / "registry.pub.json")
        handler = lambda *a, **k: http.server.SimpleHTTPRequestHandler(*a, directory=str(live), **k)
        http.server.SimpleHTTPRequestHandler.log_message = lambda *a: None
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/registry.pub.json"
        self.live = registry_payload(self.repo)

    def pin(self, public: str) -> None:
        src = self.game / "src" / "CachePal.Web" / "Services"
        src.mkdir(parents=True, exist_ok=True)
        (src / "ContentSyncService.cs").write_text(
            f'public static readonly string[] PublicKeys =\n    [\n        "{public}", // current\n    ];\n')

    def drop(self, *flags: str) -> subprocess.CompletedProcess:
        env = {"PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}", "PALPACK_REGISTRY_URL": self.url,
               "PALPACK_KEY_FILE": str(self.key_file), "CACHEPAL_GAME_REPO": str(self.game)}
        clean = {k: v for k, v in os.environ.items() if k not in ("PALPACK_KEY", "AZURE_STORAGE_CONNECTION_STRING")}
        return subprocess.run([sys.executable, str(self.repo / "tools" / "drop.py"), "--cachepal-root", str(self.game),
                               "--drop-tag", "2026-W41", *flags],
                              capture_output=True, text=True, env={**clean, **env})

    def untouched(self, before: dict) -> None:
        self.assertEqual(self.state(), before, "a dry run wrote to the clone or its origin")

    def state(self) -> dict:
        return {"head": run(["git", "-C", str(self.repo), "rev-parse", "HEAD"], check=True).stdout,
                "status": run(["git", "-C", str(self.repo), "status", "--porcelain"], check=True).stdout,
                "origin": run(["git", "-C", str(self.tmp / "origin.git"), "for-each-ref"], check=True).stdout,
                "packs": sorted(p.name for p in (self.repo / "packs").iterdir())}

    def no_dna_in(self, text: str) -> None:
        out = self.tmp / "said"
        out.mkdir(exist_ok=True)
        (out / "output.txt").write_text(text)
        r = scan(out)
        self.assertEqual(r.returncode, 0, f"the drop printed a Pal's DNA:\n{r.stdout}")

    def test_a_dry_run_with_a_version_2_fixture_row_is_green_and_writes_nothing(self):
        before = self.state()
        r = self.drop("--dry-run", "--fixture")
        said = r.stdout + r.stderr
        self.assertEqual(r.returncode, 0, said)
        self.untouched(before)
        gen = self.live["generation"] + 1
        for expected in ("its public half is ContentSyncService.PublicKeys[0]", "rehearsal green",
                         f"generation {gen} signed and pushed to the throwaway origin",
                         f"DROPS.md: generation {gen} written", "removed packs/",
                         f"would publish generation {gen} (drop 2026-W41): {len(self.live['species']) + 1} species",
                         "new: Rehearsal Fern", 'First-egg phrase: "a rehearsal, never a drop"',
                         "would stamp BarnQueue row rehearsal-fixture", "gallery hook: would mark Rehearsal Fern",
                         "no DNA in", "Dry run: nothing was pushed to GitHub"):
            self.assertIn(expected, said)
        self.no_dna_in(said)

    def test_a_row_whose_words_hold_a_dna_is_stopped_before_anything_is_signed(self):
        sys.path.insert(0, str(HERE / "tools"))
        rows = json.loads(json.dumps(__import__("importlib").import_module("drop").FIXTURE_ROWS))
        body = json.loads(rows[0]["BodyJson"])
        body["lore"] = "Hatch mine: " + mint(14, "not on a page")
        rows[0]["BodyJson"] = json.dumps(body)
        (self.tmp / "rows.json").write_text(json.dumps(rows))
        r = self.drop("--dry-run", "--rows", str(self.tmp / "rows.json"))
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("A Pal's DNA is in a file this site serves", r.stderr)
        self.assertNotIn("signing", r.stdout)

    def test_with_nothing_approved_there_is_no_drop(self):
        (self.tmp / "rows.json").write_text("[]")
        before = self.state()
        r = self.drop("--dry-run", "--rows", str(self.tmp / "rows.json"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Nothing approved and unpublished in the queue: no drop.", r.stdout)
        self.assertNotIn("signing", r.stdout)
        self.untouched(before)

    def test_a_key_the_game_does_not_pin_is_refused(self):
        other = json.loads(run(["node", "-e", NODE_KEYS], check=True).stdout)
        self.pin(other["x"])
        r = self.drop("--dry-run", "--fixture")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("is not ContentSyncService.PublicKeys[0]", r.stderr)

    def test_the_rehearsal_rows_are_for_a_dry_run_only(self):
        r = self.drop("--fixture")
        self.assertEqual(r.returncode, 2)
        self.assertIn("rehearse only: add --dry-run", r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
