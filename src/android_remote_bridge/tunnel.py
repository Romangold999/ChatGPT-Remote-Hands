"""Cloudflare Quick Tunnel manager for a per-user Termux Bridge."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .server import load_config

_URL_PATTERN = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
_REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class TunnelError(RuntimeError):
    """Raised when a user's tunnel cannot be started or managed safely."""


def _state_paths(config: dict[str, Any]) -> tuple[Path, Path, Path]:
    state_file = Path(config["state_file"]).expanduser()
    root = state_file.parent
    root.mkdir(parents=True, exist_ok=True)
    return root / "cloudflared.pid", root / "cloudflared.log", root / "cloudflared.url"


def _pid_is_our_cloudflared(pid_file: Path) -> int | None:
    try:
        pid = int(pid_file.read_text(encoding="ascii").strip())
        cmdline = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\x00", b" ").decode(
            "utf-8", errors="replace"
        )
        if "cloudflared" not in cmdline or "tunnel" not in cmdline:
            return None
        os.kill(pid, 0)
        return pid
    except (OSError, ValueError):
        return None


def _health_ok(url: str) -> bool:
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/health", timeout=4) as response:
            payload = json.loads(response.read(1024))
            return response.status == 200 and payload.get("status") == "ok"
    except (OSError, ValueError, urllib.error.URLError):
        return False


def _publish_url(repository: str, url: str) -> None:
    if not shutil.which("gh"):
        raise TunnelError("GitHub CLI (gh) is not installed")
    check = subprocess.run(
        ["gh", "auth", "status", "--hostname", "github.com"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if check.returncode != 0:
        raise TunnelError("GitHub CLI is not authenticated; run gh auth login first")
    result = subprocess.run(
        ["gh", "variable", "set", "BRIDGE_TUNNEL_URL", "--repo", repository, "--body", url],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode != 0:
        raise TunnelError("could not publish BRIDGE_TUNNEL_URL to the private repository")


def start(config_path: Path) -> str:
    config = load_config(config_path)
    repository = config["repository"]
    if not _REPOSITORY_PATTERN.fullmatch(repository):
        raise TunnelError("config repository must be OWNER/PRIVATE_REPOSITORY")
    binary = shutil.which("cloudflared")
    if not binary:
        raise TunnelError("cloudflared is missing; install it with: pkg install cloudflared")
    if not _health_ok("http://127.0.0.1:18766"):
        raise TunnelError("local Bridge is not healthy on 127.0.0.1:18766")

    pid_file, log_file, url_file = _state_paths(config)
    old_pid = _pid_is_our_cloudflared(pid_file)
    if old_pid is not None:
        if url_file.exists():
            old_url = url_file.read_text(encoding="utf-8").strip()
            if _health_ok(old_url):
                _publish_url(repository, old_url)
                return old_url
        try:
            os.killpg(old_pid, signal.SIGTERM)
        except OSError:
            pass
    pid_file.unlink(missing_ok=True)
    url_file.unlink(missing_ok=True)

    with log_file.open("ab", buffering=0) as log_stream:
        process = subprocess.Popen(
            [binary, "tunnel", "--no-autoupdate", "--url", "http://127.0.0.1:18766"],
            stdin=subprocess.DEVNULL,
            stdout=log_stream,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            close_fds=True,
        )
    os.chmod(log_file, 0o600)
    os.chmod(pid_file.parent, 0o700)
    pid_file.write_text(str(process.pid), encoding="ascii")
    os.chmod(pid_file, 0o600)

    deadline = time.monotonic() + 60
    url = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            pid_file.unlink(missing_ok=True)
            raise TunnelError("cloudflared exited before creating a tunnel; inspect local tunnel log")
        try:
            log_text = log_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            log_text = ""
        matches = _URL_PATTERN.findall(log_text)
        if matches:
            candidate = matches[-1]
            if _health_ok(candidate):
                url = candidate
                break
        time.sleep(0.5)

    if url is None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except OSError:
            pass
        pid_file.unlink(missing_ok=True)
        raise TunnelError("timed out waiting for a healthy Cloudflare Quick Tunnel")

    try:
        _publish_url(repository, url)
        url_file.write_text(url + "\n", encoding="utf-8")
        os.chmod(url_file, 0o600)
    except Exception:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except OSError:
            pass
        pid_file.unlink(missing_ok=True)
        url_file.unlink(missing_ok=True)
        raise
    return url


def _delete_published_url(repository: str) -> None:
    if not shutil.which("gh"):
        return
    subprocess.run(
        ["gh", "variable", "delete", "BRIDGE_TUNNEL_URL", "--repo", repository],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def stop(config_path: Path) -> bool:
    config = load_config(config_path)
    pid_file, _log_file, url_file = _state_paths(config)
    pid = _pid_is_our_cloudflared(pid_file)
    if pid is None:
        pid_file.unlink(missing_ok=True)
        url_file.unlink(missing_ok=True)
        _delete_published_url(config["repository"])
        return False
    try:
        os.killpg(pid, signal.SIGTERM)
    except OSError as exc:
        raise TunnelError("could not stop the recorded cloudflared process") from exc
    pid_file.unlink(missing_ok=True)
    url_file.unlink(missing_ok=True)
    _delete_published_url(config["repository"])
    return True


def status(config_path: Path) -> dict[str, Any]:
    config = load_config(config_path)
    pid_file, _log_file, url_file = _state_paths(config)
    pid = _pid_is_our_cloudflared(pid_file)
    url = url_file.read_text(encoding="utf-8").strip() if url_file.exists() else None
    return {"running": pid is not None, "pid": pid, "url": url if pid is not None else None}


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage this user's Cloudflare Quick Tunnel")
    parser.add_argument("action", choices=("start", "stop", "status"))
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.action == "start":
            print(start(args.config))
        elif args.action == "stop":
            print("stopped" if stop(args.config) else "not running")
        else:
            print(json.dumps(status(args.config), ensure_ascii=False))
    except TunnelError as exc:
        parser.exit(1, f"android-remote-bridge-tunnel: {exc}\n")


if __name__ == "__main__":
    main()
