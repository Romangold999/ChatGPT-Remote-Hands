#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

REPO_URL="https://github.com/Romangold999/Android-Remote-Bridge.git"
APP_ROOT="${HOME}/.local/share/android-remote-bridge"
SOURCE_DIR="${APP_ROOT}/source"
VENV_DIR="${APP_ROOT}/venv"
STATE_DIR="${APP_ROOT}/state"
CONFIG_DIR="${HOME}/.config/android-remote-bridge"
CONFIG_FILE="${CONFIG_DIR}/config.json"
INSTALL_STATE="${STATE_DIR}/install.json"

say() { printf '\n[Android Remote Bridge] %s\n' "$*"; }
die() { printf '\n[Android Remote Bridge] ERROR: %s\n' "$*" >&2; exit 1; }

if [[ -z "${PREFIX:-}" || "${PREFIX}" != *com.termux* ]]; then
  die "This installer must run inside the native Termux app."
fi
if [[ "$(uname -m)" != "aarch64" && "$(uname -m)" != "arm64" ]]; then
  die "The first installer release currently supports Android ARM64 only."
fi
if [[ ! -r /dev/tty ]]; then
  die "An interactive Termux session is required."
fi

mkdir -p "$APP_ROOT" "$STATE_DIR" "$CONFIG_DIR"
chmod 700 "$APP_ROOT" "$STATE_DIR" "$CONFIG_DIR"

say "Installing required Termux packages..."
pkg update -y
pkg install -y python python-cryptography git gh curl jq cloudflared

if [[ ! -d "$SOURCE_DIR/.git" ]]; then
  [[ ! -e "$SOURCE_DIR" ]] || die "Source path exists but is not a Git checkout: $SOURCE_DIR"
  git clone --depth 1 "$REPO_URL" "$SOURCE_DIR"
else
  git -C "$SOURCE_DIR" fetch --depth 1 origin main
  git -C "$SOURCE_DIR" merge --ff-only FETCH_HEAD
fi

say "Preparing the isolated Python environment..."
python -m venv --system-site-packages "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -e "$SOURCE_DIR"
"$VENV_DIR/bin/python" -c 'import jwt, cryptography' \
  || die "Termux Python cryptography module is unavailable; check the python-cryptography package."

say "Checking GitHub authorization..."
if ! gh auth status --hostname github.com >/dev/null 2>&1; then
  gh auth login --hostname github.com --git-protocol https --web
fi
gh auth status --hostname github.com >/dev/null 2>&1 || die "GitHub CLI authorization did not complete."
OWNER="$(gh api user --jq .login)"
[[ -n "$OWNER" ]] || die "Could not determine the authenticated GitHub owner."

if [[ -f "$CONFIG_FILE" ]]; then
  FULL_REPO="$("$VENV_DIR/bin/python" -c 'import json,sys; print(json.load(open(sys.argv[1]))["repository"])' "$CONFIG_FILE")"
  [[ "$FULL_REPO" == "$OWNER/"* ]] || die "Existing local config belongs to a different GitHub owner."
  REPO_NAME="${FULL_REPO#*/}"
  say "Resuming existing installation for $FULL_REPO."
else
  if [[ -f "$INSTALL_STATE" ]]; then
    FULL_REPO="$("$VENV_DIR/bin/python" -c 'import json,sys; print(json.load(open(sys.argv[1]))["repository"])' "$INSTALL_STATE")"
    [[ "$FULL_REPO" == "$OWNER/"* ]] || die "Saved installation state belongs to a different GitHub owner."
    REPO_NAME="${FULL_REPO#*/}"
    say "Resuming private repository setup for $FULL_REPO."
  else
    REPO_NAME="${ANDROID_REMOTE_BRIDGE_REPO:-android-remote-bridge}"
    while gh repo view "$OWNER/$REPO_NAME" >/dev/null 2>&1; do
      printf '\nRepository %s/%s already exists.\n' "$OWNER" "$REPO_NAME" >&2
      printf 'Enter a different new repository name: ' > /dev/tty
      IFS= read -r REPO_NAME < /dev/tty
      [[ -n "$REPO_NAME" && "$REPO_NAME" != *"/"* ]] || die "Invalid repository name."
    done
    FULL_REPO="$OWNER/$REPO_NAME"
    printf '{"repository":"%s"}\n' "$FULL_REPO" > "$INSTALL_STATE"
    chmod 600 "$INSTALL_STATE"
  fi

  if ! gh repo view "$FULL_REPO" >/dev/null 2>&1; then
    say "Creating your own private GitHub repository: $FULL_REPO"
    gh repo create "$FULL_REPO" --private --description "Private Android Remote Bridge mailbox for $OWNER"
  fi
  gh auth setup-git
  TEMP_REPO="$(mktemp -d "${TMPDIR:-$PREFIX/tmp}/arb-repo.XXXXXX")"
  cleanup() { rm -rf "$TEMP_REPO"; }
  trap cleanup EXIT

  git clone "https://github.com/$FULL_REPO.git" "$TEMP_REPO/repo" \
    || die "Could not clone the private operational repository; rerun the installer to resume."
  WORK_REPO="$TEMP_REPO/repo"
  if ! git -C "$WORK_REPO" rev-parse --verify HEAD >/dev/null 2>&1; then
    git -C "$WORK_REPO" checkout -B main
  elif [[ "$(git -C "$WORK_REPO" branch --show-current)" != "main" ]]; then
    git -C "$WORK_REPO" checkout -B main
  fi
  cp -R -n "$SOURCE_DIR/templates/operational-repo/." "$WORK_REPO/"
  git -C "$WORK_REPO" config user.name "Android Remote Bridge Installer"
  git -C "$WORK_REPO" config user.email "$OWNER@users.noreply.github.com"
  git -C "$WORK_REPO" add -A
  if ! git -C "$WORK_REPO" diff --cached --quiet; then
    git -C "$WORK_REPO" commit -m "Initialize personal Android Remote Bridge mailbox"
  fi
  git -C "$WORK_REPO" push -u origin main
  gh repo edit "$FULL_REPO" --default-branch main
  rm -rf "$TEMP_REPO"
  trap - EXIT

  "$VENV_DIR/bin/python" - "$CONFIG_FILE" "$FULL_REPO" "$STATE_DIR/replay-state.json" <<'PY'
import json
import os
import sys
from pathlib import Path

target = Path(sys.argv[1])
data = {
    "audience": "termux-bridge",
    "repository": sys.argv[2],
    "ref": "refs/heads/main",
    "state_file": sys.argv[3],
}
temporary = target.with_suffix(".tmp")
temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
os.chmod(temporary, 0o600)
temporary.replace(target)
PY
fi

REPO_OWNER="$(gh api "repos/$FULL_REPO" --jq .owner.login)"
REPO_VISIBILITY="$(gh api "repos/$FULL_REPO" --jq .visibility)"
[[ "$REPO_OWNER" == "$OWNER" && "$REPO_VISIBILITY" == "private" ]] \
  || die "The operational repository owner or visibility check failed."

if ! curl --fail --silent http://127.0.0.1:18766/health | jq -e '.status == "ok"' >/dev/null 2>&1; then
  say "Starting your local Bridge listener..."
  nohup "$VENV_DIR/bin/android-remote-bridge" --config "$CONFIG_FILE" \
    >> "$STATE_DIR/bridge.log" 2>&1 < /dev/null &
  BRIDGE_PID=$!
  printf '%s\n' "$BRIDGE_PID" > "$STATE_DIR/bridge.pid"
  chmod 600 "$STATE_DIR/bridge.pid" "$STATE_DIR/bridge.log" 2>/dev/null || true
  for _ in $(seq 1 30); do
    if curl --fail --silent http://127.0.0.1:18766/health | jq -e '.status == "ok"' >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
fi
curl --fail --silent http://127.0.0.1:18766/health | jq -e '.status == "ok"' >/dev/null \
  || die "Local Bridge did not become healthy. Check $STATE_DIR/bridge.log"

say "Starting the personal Cloudflare Quick Tunnel and updating your private repo..."
TUNNEL_URL="$("$VENV_DIR/bin/android-remote-bridge-tunnel" start --config "$CONFIG_FILE")"

say "Installation completed."
printf '\nPrivate repository: %s\n' "$FULL_REPO"
printf 'Tunnel URL: %s\n' "$TUNNEL_URL"
printf '\nThe Bridge and tunnel are running in the background while Android allows them to run.\n'
printf 'Quick Tunnel URLs change after a restart; run the tunnel start command again to publish the new URL.\n'
printf 'Termux:Boot is not enabled automatically.\n'
