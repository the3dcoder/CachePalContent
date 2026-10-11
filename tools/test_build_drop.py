#!/usr/bin/env python3
"""Checks for tools/build-drop.py, run in throwaway copies of this repository.

    python3 tools/test_build_drop.py            (or: python3 -m unittest tools/test_build_drop.py)

Each check copies the repository (without .git) into a temporary directory, puts a stub `az`
(serving the approved BarnQueue rows below) and a stub `dotnet` (minting a fixed premiere code) on
PATH, runs that copy's build-drop.py, and reads the species file it wrote. The last step runs the
copy's `palpack.mjs validate`, so what build-drop writes is what palpack signs. Nothing touches
this clone, Azure or the network.

The rows' BodyJson is spelled as the Barn api stores it (CachePal `SpeciesSubmission.ToJson()`):
version 1 rows carry the grids and words; version 2 rows (studio-v2, 2026-10-11) also carry the
maker's coat, shiny coat, shape, appetite, three stage lines and second frames, so the drop needs
no hand-written overlay file.

The game repository (for palpack's overlay rulebook, tools/palpack-overlays.mjs) is found as
palpack finds it: CACHEPAL_GAME_REPO, else the sibling clone.
"""

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
GAME = os.environ.get("CACHEPAL_GAME_REPO") or str(HERE.parent / "CachePal")
PREMIERE = "11111111-2222-4333-8444-555555555555"

GRID = [
    "................", "................", "....OOOOOOOO....", "...OBBBBBBBBO...",
    "..OBBWEBBWEBBO..", "..OBBEEBBEEBBO..", "..OBBBBBBBBBBO..", "..OBBBMMBBBBBO..",
    "..OBCBBBBBCBBO..", "..OBBSSSSSSBBO..", "..OABSSSSSSBAO..", "...OBBSSSSBBO...",
    "....OBBBBBBO....", ".....OOOOOO.....", "................", "................",
]


def grid(marker: str = ".", feet: bool = False) -> list[str]:
    g = list(GRID)
    g[15] = marker + "." * 15
    if feet:
        g[13] = "....OO....OO...."
    return g


def overlay(kind: str, stage: str, row: int = 6) -> dict:
    cells = ["." * 16 for _ in range(16)]
    cells[row] = "....XXXXXXXX...."
    return {"kind": kind, "stage": stage, "grid": cells}


def v1_body(name: str, **extra) -> dict:
    body = {
        "name": name, "element": "Bloom", "lore": f"{name} naps on warm stones.",
        "biasPower": 1, "biasMischief": 0, "biasStealth": 0, "biasResilience": -1, "biasLuck": 0, "biasSignal": 0,
        "suggestedWeight": 60, "requestedSeed": "",
        "gridBaby": grid("A"), "gridTeen": grid("S"), "gridAdult": grid("C"), "gridElder": [], "overlays": [],
    }
    body.update(extra)
    return body


V2_CHOICES = {
    "version": 2,
    "baseColor": "#63ab3f", "shinyColor": "#f0b541", "bodyArchetype": "quad",
    "hungryFor": "berry mix", "needDecayBias": [1.2, 1, 0.9, 1, 0.9],
    "babyDescription": "A sprout with ideas.", "teenDescription": "Taller now, and twice as nosy.",
    "adultDescription": "A friend with bark and a good ear.",
}


def row(row_key: str, type_: str, body: dict, submitter: str = "mossmaker") -> dict:
    return {"PartitionKey": "q", "RowKey": row_key, "Type": type_, "Status": "approved",
            "SubmitterName": submitter, "BodyJson": json.dumps(body, ensure_ascii=False, separators=(",", ":"))}


AZ_STUB = r'''#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
flt = args[args.index("--filter") + 1] if "--filter" in args else ""
rows = json.load(open(os.environ["BUILD_DROP_ROWS"]))
for t in ("species-submission", "species-revision", "dex-edit"):
    if f"Type eq '{t}'" in flt:
        print(json.dumps({"items": [r for r in rows if r["Type"] == t]}))
        break
else:
    print(json.dumps({"items": []}))
'''

DOTNET_STUB = f'''#!/usr/bin/env python3
print("{PREMIERE}|v2|stub")
'''


class Drop:
    """A throwaway copy of the repository, ready to run its build-drop.py."""

    def __init__(self, rows: list[dict], overlays: dict[str, dict] | None = None):
        self.tmp = Path(tempfile.mkdtemp(prefix="build-drop-check-"))
        self.repo = self.tmp / "content"
        shutil.copytree(HERE, self.repo, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        for name, text in (("az", AZ_STUB), ("dotnet", DOTNET_STUB)):
            path = self.bin / name
            path.write_text(text)
            path.chmod(path.stat().st_mode | stat.S_IEXEC)
        (self.tmp / "rows.json").write_text(json.dumps(rows))
        self.overlays = self.tmp / "overlays"
        self.overlays.mkdir()
        for key, data in (overlays or {}).items():
            (self.overlays / f"{key}.overlay.json").write_text(json.dumps(data))

    def run(self) -> subprocess.CompletedProcess:
        env = {**os.environ, "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
               "AZURE_STORAGE_CONNECTION_STRING": "stub", "BUILD_DROP_ROWS": str(self.tmp / "rows.json")}
        return subprocess.run([sys.executable, str(self.repo / "tools" / "build-drop.py"), "--cachepal-root", GAME,
                               "--overlays", str(self.overlays), "--drop-tag", "2026-W41"],
                              capture_output=True, text=True, env=env)

    def species(self, key: str) -> dict:
        return json.loads((self.repo / "species" / f"{key}.json").read_text())

    def validate(self) -> subprocess.CompletedProcess:
        node = os.environ.get("NODE") or shutil.which("node") or "node"
        return subprocess.run([node, str(self.repo / "tools" / "palpack.mjs"), "validate"], capture_output=True, text=True,
                              env={**os.environ, "CACHEPAL_GAME_REPO": GAME})

    def close(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)


HAND_OVERLAY = {
    "baseColor": "#7BC67E", "shinyColor": "#FFD54F", "bodyArchetype": "blob", "hungryFor": "damp moss",
    "needDecayBias": [1.0, 1.0, 1.0, 1.0, 1.0], "babyDescription": "A small one.",
    "teenDescription": "A middling one.", "adultDescription": "A grown one.",
}


class NewSpecies(unittest.TestCase):
    def tearDown(self):
        for d in getattr(self, "drops", []):
            d.close()

    def drop(self, rows, overlays=None) -> Drop:
        d = Drop(rows, overlays)
        self.drops = [*getattr(self, "drops", []), d]
        return d

    def test_a_painted_overlay_reaches_the_species_file(self):
        painted = [overlay("marking", "teen"), overlay("accessory", "adult", 12)]
        d = self.drop([row("2", "species-submission", v1_body("Mossbit", overlays=painted))], {"mossbit": HAND_OVERLAY})
        result = d.run()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(d.species("mossbit").get("overlays"), painted,
                         "the overlays the maker painted were dropped on the way to the pack")

    def test_a_version_2_row_needs_no_hand_written_overlay_file(self):
        body = v1_body("Fernwhistle", **V2_CHOICES, gridAdultB=grid("C", feet=True), gridTeenB=grid("S", feet=True),
                       overlays=[overlay("marking", "adult")])
        d = self.drop([row("2", "species-submission", body)])
        result = d.run()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        s = d.species("fernwhistle")
        for field in ("baseColor", "shinyColor", "bodyArchetype", "hungryFor", "needDecayBias",
                      "babyDescription", "teenDescription", "adultDescription"):
            self.assertEqual(s[field], V2_CHOICES[field], field)
        self.assertEqual(s["gridAdultB"], body["gridAdultB"])
        self.assertEqual(s["gridTeenB"], body["gridTeenB"])
        self.assertNotIn("gridBabyB", s, "a frame the maker did not draw is none, so frame A plays alone")
        self.assertEqual(s["overlays"], body["overlays"])
        self.assertEqual((s["schema"], s["premiereDna"], s["createdBy"]), ("cachepal-pack-v2", PREMIERE, "mossmaker"))
        check = d.validate()
        self.assertEqual(check.returncode, 0, check.stderr + check.stdout)

    def test_a_version_1_row_still_needs_its_overlay_file(self):
        d = self.drop([row("2", "species-submission", v1_body("Pebblenook"))])
        result = d.run()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("MISSING OVERLAY", result.stderr + result.stdout)

    def test_a_version_1_row_with_its_file_builds_as_before_and_validates(self):
        d = self.drop([row("2", "species-submission", v1_body("Pebblenook"))], {"pebblenook": HAND_OVERLAY})
        result = d.run()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        s = d.species("pebblenook")
        for field, value in HAND_OVERLAY.items():
            self.assertEqual(s[field], value, field)
        self.assertNotIn("overlays", s, "nothing painted, nothing carried")
        check = d.validate()
        self.assertEqual(check.returncode, 0, check.stderr + check.stdout)

    def test_a_version_2_row_whose_choices_are_incomplete_is_refused_not_guessed(self):
        body = v1_body("Halfdone", **{**V2_CHOICES, "hungryFor": None})
        d = self.drop([row("2", "species-submission", {k: v for k, v in body.items() if v is not None})])
        result = d.run()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("INCOMPLETE VERSION 2 ROW for Halfdone: hungryFor", result.stderr + result.stdout)


class Revisions(unittest.TestCase):
    """A revision of a live species that already has second frames (glowtail)."""

    def setUp(self):
        self.live = json.loads((HERE / "species" / "glowtail.json").read_text())
        self.assertIn("gridBabyB", self.live, "the fixture species must have second frames for these checks to mean anything")

    def revise(self, **changes) -> tuple[Drop, dict]:
        body = v1_body(self.live["name"], targetSpeciesId=self.live["id"], **changes)
        d = Drop([row("1", "species-revision", body)])
        self.addCleanup(d.close)
        result = d.run()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        return d, d.species(self.live["key"])

    def test_a_version_2_revision_carries_its_choices_frames_and_overlays(self):
        d, s = self.revise(version=2, baseColor="#4fa4b8", teenDescription="Brighter at dusk.",
                           gridAdultB=grid("C", feet=True), overlays=[overlay("marking", "adult")])
        self.assertEqual(s["baseColor"], "#4fa4b8")
        self.assertEqual(s["teenDescription"], "Brighter at dusk.")
        self.assertEqual(s["shinyColor"], self.live["shinyColor"], "a choice left out keeps the live one")
        self.assertEqual(s["hungryFor"], self.live["hungryFor"])
        self.assertEqual(s["gridAdultB"], grid("C", feet=True))
        self.assertNotIn("gridBabyB", s, "in version 2 an absent second frame is none: the old pose would not fit the new art")
        self.assertEqual(s["overlays"], [overlay("marking", "adult")])
        last = s["history"][-1]["change"]
        for word in ("art", "colours", "lines", "overlays"):
            self.assertIn(word, last)
        check = d.validate()
        self.assertEqual(check.returncode, 0, check.stderr + check.stdout)

    def test_a_version_1_revision_leaves_the_second_frames_and_choices_alone(self):
        body_without_overlays = {k: v for k, v in v1_body(self.live["name"]).items() if k != "overlays"}
        d = Drop([row("1", "species-revision", {**body_without_overlays, "targetSpeciesId": self.live["id"]})])
        self.addCleanup(d.close)
        result = d.run()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        s = d.species(self.live["key"])
        for field in ("gridBabyB", "gridTeenB", "gridAdultB", "baseColor", "bodyArchetype", "hungryFor", "adultDescription"):
            self.assertEqual(s.get(field), self.live.get(field), field)


if __name__ == "__main__":
    unittest.main(verbosity=2)
