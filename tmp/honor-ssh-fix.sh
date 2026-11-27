#!/data/data/com.termux/files/usr/bin/bash
set -eu

# Add the Tank 2 public key to this Honor Termux account.
KEY='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIApSScRDJXqNUsCOO6Qx79tyu8dND9I6z7A/VTTFlf2c tank2-to-honor-termux'
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
