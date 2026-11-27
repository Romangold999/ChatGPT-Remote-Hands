"""Lifecycle CLI for the local Android Remote Bridge listener."""
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import deque
from pathlib import Path

from .server import load_config


class BridgeCLIError(RuntimeError):
    """Raised when the local Bridge cannot be managed safely."""


def _paths(config_path: Path) -> tuple[Path, Path]:
    config = load_config(config_path)
    root = Path(config["state_file"]).expanduser().parent
    root.mkdir(parents=True, exist_ok=True)
    return root / "bridge.pid", root / "bridge.log"


def _health_ok(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as response:
            return response.status == 200 and response.read(256).find(b'"status":"ok"') >= 0
    except (OSError, urllib.error.URLError):
        return False


def _matching_pid(pid_file: Path, config_path: Path) -> int | None:
    try:
        pid = int(pid_file.read_text(encoding="ascii").strip())
        command = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\x00", b" ").decode(
            "utf-8", errors="replace"
        )
        expected_config = str(config_path.expanduser().resolve())
        if (
            "android_remote_bridge.server" not in command
            or "--config" not in command
            or expected_config not in command
        ):
            return None
        os.kill(pid, 0)
        return pid
    except (OSError, ValueError):
        return None


def start(config_path: Path) -> int:
    config_path = config_path.expanduser().resolve()
    config = load_config(config_path)
    port = config["port"]
    pid_file, log_file = _paths(config_path)
    pid = _matching_pid(pid_file, config_path)
    if pid is not None:
        if _health_ok(port):
            return pid
        raise BridgeCLIError("a Bridge process is recorded but not healthy; inspect logs or stop it first")
    if _health_ok(port):
        raise BridgeCLIError(f"port {port} is already serving another process; refusing to take it over")

    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("ab", buffering=0) as log:
        process = subprocess.Popen(
            [sys.executable, "-m", "android_remote_bridge.server", "--config", str(config_path)],
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            close_fds=True,
        )
    os.chmod(log_file, 0o600)
    os.chmod(log_file.parent, 0o700)
    pid_file.write_text(str(process.pid), encoding="ascii")
    os.chmod(pid_file, 0o600)

    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if process.poll() is not None:
            pid_file.unlink(missing_ok=True)
            raise BridgeCLIError("listener exited during startup; inspect bridge.log")
        if _health_ok(port):
            return process.pid
        time.sleep(0.25)

    try:
        os.killpg(process.pid, signal.SIGTERM)
    except OSError:
        pass
    pid_file.unlink(missing_ok=True)
    raise BridgeCLIError("listener did not become healthy within 20 seconds")


def stop(config_path: Path) -> bool:
    config_path = config_path.expanduser().resolve()
    pid_file, _log_file = _paths(config_path)
    pid = _matching_pid(pid_file, config_path)
    if pid is None:
        pid_file.unlink(missing_ok=True)
        return False
    try:
        os.killpg(pid, signal.SIGTERM)
    except OSError as exc:
        raise BridgeCLIError("could not signal the recorded Bridge process") from exc
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except OSError:
            break
        time.sleep(0.2)
    else:
        try:
            os.killpg(pid, signal.SIGKILL)
        except OSError:
            pass
    pid_file.unlink(missing_ok=True)
    return True


def status(config_path: Path) -> dict[str, object]:
    config_path = config_path.expanduser().resolve()
    config = load_config(config_path)
    pid_file, _log_file = _paths(config_path)
    pid = _matching_pid(pid_file, config_path)
    return {"running": pid is not None and _health_ok(config["port"]), "pid": pid}


def show_logs(config_path: Path, lines: int = 50) -> str:
    _pid_file, log_file = _paths(config_path)
    if not log_file.exists():
        return "No Bridge log has been created yet."
    with log_file.open(encoding="utf-8", errors="replace") as stream:
        return "".join(deque(stream, maxlen=lines))


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage the local Android Remote Bridge")
    parser.add_argument("action", choices=("start", "stop", "status", "logs"))
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--lines", type=int, default=50)
    args = parser.parse_args()
    try:
        if args.action == "start":
            print(f"running (pid {start(args.config)})")
        elif args.action == "stop":
            print("stopped" if stop(args.config) else "not running")
        elif args.action == "status":
            print(status(args.config))
        else:
            if not 1 <= args.lines <= 500:
                raise BridgeCLIError("--lines must be between 1 and 500")
            print(show_logs(args.config, args.lines), end="")
    except BridgeCLIError as exc:
        parser.exit(1, f"android-remote-bridge: {exc}\n")


if __name__ == "__main__":
    main()
