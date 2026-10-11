#!/usr/bin/env bash
# Publish a content drop. Run by the agent, not by a person.
#
#   ./tools/publish-drop.sh 21
#
# The whole drop, from the queue to the stamped rows, is one command that runs this one:
# `python3 tools/drop.py` (rehearse first with `--dry-run`). This script is its signing step.
#
# WHO RUNS THIS. Not the owner. Publishing is meant to be something you ask for — "publish
# generation 11" — and not a procedure you carry out. The signing key lives in the environment's
# configured variables, so every agent session already has it and the publish is just work like
# any other. If you are a person reading this because something went wrong, the whole thing is
# `node tools/palpack.mjs publish` with three environment variables; everything below is guards.
#
# WHERE THE KEY COMES FROM. `PALPACK_KEY` when the environment has it, else the key file
# (`PALPACK_KEY_FILE`, default `~/.cachepal/signing.key`, mode 600), which is where the owner's PC
# holds it since 2026-10-11 (its canonical copy is the Key Vault `cachepal-kv`; the game repo's
# docs/runbooks/CREDENTIALS.md). Never in this repo, a shell profile or a CI service.
#
# NO DNA ON A SERVED PAGE. A DNA GUID is a clone code, and Pages serves every file here. So before
# signing, `tools/dna-scan.py --before-signing` must find none outside packs/; after signing,
# `--prune` removes each superseded pack that held one (packs carried the first egg's DNA until
# 2026-10-11) and the whole tree must scan clean, or nothing is committed or pushed.
#
# TWO OPTIONAL INPUTS, both from tools/drop.py:
#   PUBLISH_DROP_NOTES=<file>   this drop's section for DROPS.md, with @GENERATION@ where the number
#                               goes. It lands in the same commit as the signed registry, so the ledger
#                               never names a generation that was not signed.
#   PUBLISH_DROP_REHEARSAL=1    a rehearsal in a throwaway copy: refuses unless `origin` is a local
#                               path, and does not watch the CDN (nothing was published to it).
#
# WHY YOU STILL PASS THE COUNT. It is the one argument, and it is the check. Generation 10's
# first attempt signed a SIX-species tree while eighteen were being published (B350). The only
# thing that catches that is somebody stating what they meant and the machine disagreeing; a
# count this script read off the tree would be the tree checking itself, which catches nothing.
# The agent takes the number from whoever asked for the drop.
set -euo pipefail

cd "$(dirname "$0")/.."
REGISTRY_URL="${PALPACK_REGISTRY_URL:-https://the3dcoder.github.io/CachePalContent/registry.pub.json}"

die() { printf '\n\033[31m✘ %s\033[0m\n' "$*" >&2; exit 1; }
say() { printf '\033[36m▸\033[0m %s\n' "$*"; }

# ---- the number ---------------------------------------------------------------------------
COUNT="${1:-}"
[ -n "$COUNT" ] || die "How many species should this publish?

    ./tools/publish-drop.sh <count>

That number is the check (B350). Count them; do not read it off the tree."
case "$COUNT" in ''|*[!0-9]*) die "'$COUNT' is not a count." ;; esac

# ---- the key ------------------------------------------------------------------------------
if [ -n "${PALPACK_KEY:-}" ]; then
  say "using PALPACK_KEY from the environment"
else
  KEY_FILE="${PALPACK_KEY_FILE:-$HOME/.cachepal/signing.key}"
  [ -f "$KEY_FILE" ] || die "No signing key: PALPACK_KEY is not set and there is no $KEY_FILE.

Place it from the vault (the game repo's docs/runbooks/CREDENTIALS.md has the one command)."
  # A key any local process can read is a key worth re-storing. Warn, do not refuse: a wrong
  # mode is a housekeeping problem, and refusing to publish over it would be this script
  # inventing a ceremony of its own.
  MODE="$(stat -c '%a' "$KEY_FILE" 2>/dev/null || stat -f '%Lp' "$KEY_FILE" 2>/dev/null || echo '')"
  case "$MODE" in 600|400) ;; '') ;; *) printf '\033[33m!\033[0m %s is mode %s — chmod 600 it.\n' "$KEY_FILE" "$MODE" ;; esac
  PALPACK_KEY="$(cat "$KEY_FILE")"
  export PALPACK_KEY
  say "key read from $KEY_FILE"
fi

# ---- a rehearsal pushes only to a throwaway --------------------------------------------------
REHEARSAL="${PUBLISH_DROP_REHEARSAL:-}"
if [ -n "$REHEARSAL" ]; then
  ORIGIN_URL="$(git remote get-url origin)"
  case "$ORIGIN_URL" in
    *://*|*@*:*) die "A rehearsal pushes only to a local throwaway origin, and origin is $ORIGIN_URL." ;;
  esac
  say "rehearsal: origin is the throwaway $ORIGIN_URL"
fi

# ---- the tree -----------------------------------------------------------------------------
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
[ "$BRANCH" = "main" ] || die "On '$BRANCH'. Drops publish from main — merge your branch first."
[ -z "$(git status --porcelain)" ] || die "Working tree is dirty. Commit or stash first: what gets
signed is HEAD, so an uncommitted edit would be published without being recorded."

git fetch -q origin main
LOCAL="$(git rev-parse HEAD)"; REMOTE="$(git rev-parse origin/main)"
[ "$LOCAL" = "$REMOTE" ] || die "main and origin/main disagree. Pull or push first — publishing
from a diverged tree is how a drop gets signed that nobody can reproduce."

ON_DISK="$(ls species/*.json 2>/dev/null | wc -l | tr -d ' ')"
say "commit $(git rev-parse --short HEAD) · $ON_DISK species on disk · you asked for $COUNT"

# ---- what is live now ---------------------------------------------------------------------
BEFORE="$(curl -fsS --max-time 30 "$REGISTRY_URL" 2>/dev/null | node -e "
  let s='';process.stdin.on('data',d=>s+=d).on('end',()=>{
    try{const p=JSON.parse(Buffer.from(JSON.parse(s).payload,'base64url').toString());
    console.log('generation '+p.generation+', '+p.species.length+' species');}catch(e){console.log('');}});" || echo '')"
[ -n "$BEFORE" ] && say "live now: $BEFORE" || say "could not read the live registry — publish will decide"
BEFORE_GEN="$(printf '%s' "$BEFORE" | sed -n 's/^generation \([0-9]*\),.*/\1/p')"

# ---- no DNA, before a byte is signed ---------------------------------------------------------
python3 tools/dna-scan.py --before-signing || die "A Pal's DNA is in a file this site serves (above).
Print the first-egg phrase instead. Nothing was signed."

# ---- sign ----------------------------------------------------------------------------------
say "signing…"
PALPACK_EXPECT_SPECIES="$COUNT" PALPACK_EXPECT_COMMIT="$LOCAL" node tools/palpack.mjs publish

[ -n "$(git status --porcelain)" ] || die "publish wrote nothing. Refusing to report a drop
that did not happen."

UNPUSHED="The generation is signed in this working tree and NOT pushed: nothing reached players.
Discard it with: git checkout -- . && git clean -fdq packs cosmetics"

# ---- the ledger, in the same commit as the generation it describes ----------------------------
if [ -n "${PUBLISH_DROP_NOTES:-}" ]; then
  [ -f "$PUBLISH_DROP_NOTES" ] || die "PUBLISH_DROP_NOTES names $PUBLISH_DROP_NOTES, which is not there. $UNPUSHED"
  python3 - "$PUBLISH_DROP_NOTES" <<'PY' || die "Could not write the drop into DROPS.md. $UNPUSHED"
import base64, json, sys
from pathlib import Path
gen = json.loads(base64.urlsafe_b64decode(json.loads(Path("registry.pub.json").read_text())["payload"] + "==="))["generation"]
notes = Path(sys.argv[1]).read_text().replace("@GENERATION@", str(gen)).strip() + "\n\n"
drops = Path("DROPS.md").read_text()
head = "# Content drops\n\n"
assert drops.startswith(head), "DROPS.md does not start with its title"
rest = drops[len(head):]
# Below the standing note at the top (a block quote), above the newest generation.
cut = rest.find("\n## ")
at = len(head) + (cut + 1 if rest.startswith(">") and cut >= 0 else 0)
Path("DROPS.md").write_text(drops[:at] + notes + drops[at:])
print(f"\u25b8 DROPS.md: generation {gen} written")
PY
fi

# ---- and no DNA in anything this generation leaves served ------------------------------------
python3 tools/dna-scan.py --prune || die "A Pal's DNA would be served (above). $UNPUSHED"

# ---- record and push ------------------------------------------------------------------------
git add -A
git commit -q -m "drops: publish $COUNT species"
git push -q origin main
say "pushed $(git rev-parse --short HEAD)"

if [ -n "$REHEARSAL" ]; then
  GEN_NOW="$(node -e "console.log(JSON.parse(Buffer.from(require('./registry.pub.json').payload,'base64url')).generation)")"
  printf '\n\033[32m✔ rehearsal: generation %s signed and pushed to the throwaway origin — %s species\033[0m\n' "$GEN_NOW" "$COUNT"
  exit 0
fi

# ---- and confirm it is really serving --------------------------------------------------------
say "waiting for the CDN…"
for _ in $(seq 1 30); do
  NOW="$(curl -fsS --max-time 20 "$REGISTRY_URL" 2>/dev/null | node -e "
    let s='';process.stdin.on('data',d=>s+=d).on('end',()=>{
      try{const p=JSON.parse(Buffer.from(JSON.parse(s).payload,'base64url').toString());
      console.log(p.generation+' '+p.species.length);}catch(e){console.log('');}});" || echo '')"
  set -- $NOW
  # B475's publish taught this loop a lesson: the count alone cannot tell generations apart.
  # A grids-only drop keeps the species count, so a stale edge still serving the PREVIOUS
  # generation matched "27 = 27" and this line announced the old generation as the new drop.
  # The generation must have MOVED past the baseline read before signing.
  if [ "${2:-}" = "$COUNT" ] && [ "${1:-0}" != "${BEFORE_GEN:-}" ]; then
    printf '\n\033[32m✔ generation %s is live — %s species\033[0m\n' "$1" "$2"
    exit 0
  fi
  sleep 20
done

# NOT a failure of the publish. The signed bytes are pushed; only the watcher gave up. Said
# plainly, because the one genuinely bad move here is re-running a drop that already landed.
printf '\n\033[33m! The drop IS signed and pushed. The CDN has not caught up yet — that is all
  this last step watches. Check %s in a few minutes.
  Do NOT re-run this: the drop landed.\033[0m\n' "$REGISTRY_URL"
