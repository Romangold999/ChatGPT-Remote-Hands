#!/data/data/com.termux/files/usr/bin/bash
set -eu

# Install the Tank 2 public key in this Termux user's authorized_keys.
KEY_FILE="$HOME/.ssh/id_ed25519.pub"
if [ ! -f "$KEY_FILE" ]; then
  echo "ERROR: Tank 2 public key file was not found."
  exit 1
fi

KEY="$(cat "$KEY_FILE")"
SSH_DIR="$HOME/.ssh"
AUTH="$SSH_DIR/authorized_keys"

mkdir -p "$SSH_DIR"
chmod 700 "$SSH_DIR"
touch "$AUTH"
chmod 600 "$AUTH"

if ! grep -Fqx "$KEY" "$AUTH"; then
  printf '%s\n' "$KEY" >> "$AUTH"
fi

echo "=== HONOR SSH SETUP ==="
echo "User: $(whoami)"
echo "Home: $HOME"
echo "Authorized key fingerprints:"
ssh-keygen -lf "$AUTH" 2>&1 || true

if ! pgrep -f '[s]shd' >/dev/null 2>&1; then
  echo "Starting Termux sshd..."
  sshd
fi

echo "Done. Existing authorized_keys entries were preserved."
