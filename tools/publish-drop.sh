#!/usr/bin/env bash
# Publish a content drop. Run by the agent, not by a person.
#
#   ./tools/publish-drop.sh 21
#
# WHO RUNS THIS. Not the owner. Publishing is meant to be something you ask for — "publish
# generation 11" — and not a procedure you carry out. The signing key lives in the environment's
# configured variables, so every agent session already has it and the publish is just work like
# any other. If you are a person reading this because something went wrong, the whole thing is
# `node tools/palpack.mjs publish` with three environment variables; everything below is guards.
#
# WHERE THE KEY COMES FROM. `PALPACK_KEY`, out of the environment. Set once in the Claude Code
# environment settings and never again — not in this repo, not in a shell, not in a CI service.
# The fallback file path below exists only so a hand-run on a laptop still works; it is not the
# intended route and nobody should need it.
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
  [ -f "$KEY_FILE" ] || die "No signing key.

PALPACK_KEY is not in the environment. It belongs in the Claude Code environment settings,
set once, so every session has it and publishing needs nobody to fetch anything.

(A file at $KEY_FILE also works, but that is the laptop fallback, not the route.)"
  # A key any local process can read is a key worth re-storing. Warn, do not refuse: a wrong
  # mode is a housekeeping problem, and refusing to publish over it would be this script
  # inventing a ceremony of its own.
  MODE="$(stat -c '%a' "$KEY_FILE" 2>/dev/null || stat -f '%Lp' "$KEY_FILE" 2>/dev/null || echo '')"
  case "$MODE" in 600|400) ;; '') ;; *) printf '\033[33m!\033[0m %s is mode %s — chmod 600 it.\n' "$KEY_FILE" "$MODE" ;; esac
  PALPACK_KEY="$(cat "$KEY_FILE")"
  export PALPACK_KEY
  say "key read from $KEY_FILE"
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

# ---- sign ----------------------------------------------------------------------------------
say "signing…"
PALPACK_EXPECT_SPECIES="$COUNT" PALPACK_EXPECT_COMMIT="$LOCAL" node tools/palpack.mjs publish

[ -n "$(git status --porcelain)" ] || die "publish wrote nothing. Refusing to report a drop
that did not happen."

# ---- record and push ------------------------------------------------------------------------
git add -A
git commit -q -m "drops: publish $COUNT species"
git push -q origin main
say "pushed $(git rev-parse --short HEAD)"

# ---- and confirm it is really serving --------------------------------------------------------
say "waiting for the CDN…"
for _ in $(seq 1 30); do
  NOW="$(curl -fsS --max-time 20 "$REGISTRY_URL" 2>/dev/null | node -e "
    let s='';process.stdin.on('data',d=>s+=d).on('end',()=>{
      try{const p=JSON.parse(Buffer.from(JSON.parse(s).payload,'base64url').toString());
      console.log(p.generation+' '+p.species.length);}catch(e){console.log('');}});" || echo '')"
  set -- $NOW
  if [ "${2:-}" = "$COUNT" ]; then
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
