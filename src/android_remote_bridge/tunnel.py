"""Stable tunnl.gg SSH reverse-tunnel manager for a per-user Termux Bridge.

The tunnel is an ordinary OpenSSH reverse forward. Each installation owns its
own Ed25519 key; the private key never leaves the Android device.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .server import load_config

HOST = "proxy.tunnl.gg"
KNOWN_HOST_LINE = (
    "proxy.tunnl.gg ssh-ed25519 "
    "AAAAC3NzaC1lZDI1NTE5AAAAIN3HFkIcqgWI6Sa1E31KiUbcfcrX/5MZl4LnaQnUYL8K"
)
HOST_FINGERPRINT = "SHA256:5uQ6VobmUpY4wyMmm5jnAwFtt3aX06WYDDM4ER+2WUw"
_URL_PATTERN = re.compile(r"https://[a-z0-9-]+\.tunnl\.gg")
_REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class TunnelError(RuntimeError):
    """Raised when a user's tunnel cannot be started or managed safely."""


def _paths(config: dict[str, Any]) -> tuple[Path, Path, Path, Path, Path]:
    state_root = Path(config["state_file"]).expanduser().parent
    state_root.mkdir(parents=True, exist_ok=True)
    ssh_root = Path(config.get("ssh_dir", "~/.ssh")).expanduser()
    key_file = Path(config.get("tunnel_key", str(ssh_root / "android-remote-bridge_ed25519"))).expanduser()
    known_hosts = Path(config.get("known_hosts", str(ssh_root / "known_hosts_android_remote_bridge"))).expanduser()
    return (
        state_root / "tunnl.pid",
        state_root / "tunnl.log",
        state_root / "tunnl.url",
        key_file,
        known_hosts,
    )


def _publish_url(repository: str, url: str) -> None:
    """Publish the stable URL as mailbox/tunnel-url.txt, as in push-bridge."""
    if not shutil.which("gh"):
        raise TunnelError("GitHub CLI (gh) is not installed")
    check = subprocess.run(
        ["gh", "auth", "status", "--hostname", "github.com"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if check.returncode:
        raise TunnelError("GitHub CLI is not authenticated; run gh auth login first")
    path = "mailbox/tunnel-url.txt"
    lookup = subprocess.run(
        ["gh", "api", f"repos/{repository}/contents/{path}?ref=main", "--jq", ".sha"],
        capture_output=True, text=True, check=False,
    )
    if lookup.returncode != 0 or not lookup.stdout.strip():
        raise TunnelError("could not read mailbox/tunnel-url.txt in the private repository")
    encoded = base64.b64encode((url.rstrip("/") + "\\n").encode("utf-8")).decode("ascii")
    result = subprocess.run(
        [
            "gh", "api", f"repos/{repository}/contents/{path}", "--method", "PUT",
            "-f", "message=Update stable tunnl.gg URL",
            "-f", f"content={encoded}",
            "-f", f"sha={lookup.stdout.strip()}",
            "-f", "branch=main",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode:
        raise TunnelError("could not publish stable URL to mailbox/tunnel-url.txt")


def _delete_published_url(repository: str) -> None:
    # Keep the last stable URL in the mailbox, matching the working push-bridge.
    return


def _prepare_known_hosts(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    matching = [line for line in lines if line.split() and line.split()[0] == HOST]
    if matching and KNOWN_HOST_LINE not in matching:
        raise TunnelError("stored tunnl.gg host key differs from the published ED25519 fingerprint")
    if not matching:
        with path.open("a", encoding="utf-8") as stream:
            stream.write(KNOWN_HOST_LINE + "\n")
    os.chmod(path, 0o600)


def _ssh_base(key_file: Path, known_hosts: Path) -> list[str]:
    ssh = shutil.which("ssh")
    if not ssh:
        raise TunnelError("OpenSSH is missing; install it with: pkg install openssh")
    if not key_file.is_file():
        raise TunnelError(f"dedicated tunnl.gg SSH key is missing: {key_file}")
    return [
        ssh, "-i", str(key_file), "-o", "IdentitiesOnly=yes",
        "-o", f"UserKnownHostsFile={known_hosts}",
        "-o", "StrictHostKeyChecking=yes",
        "-o", "ServerAliveInterval=30",
        "-o", "ServerAliveCountMax=3",
        "-o", "ExitOnForwardFailure=yes",
    ]


def register(config_path: Path) -> None:
    config = load_config(config_path)
    _pid, _log, _url, key_file, known_hosts = _paths(config)
    _prepare_known_hosts(known_hosts)
    if not key_file.is_file():
        raise TunnelError("SSH key is not generated yet; run the installer first")
    command = _ssh_base(key_file, known_hosts) + ["-t", "link@" + HOST]
    result = subprocess.run(command, check=False)
    if result.returncode:
        raise TunnelError("tunnl.gg key registration session failed; inspect the message above")


def _health_ok(url: str) -> bool:
    try:
        request = urllib.request.Request(
            url.rstrip("/") + "/health",
            headers={"User-Agent": "Android-Remote-Bridge-health/1"},
        )
        with urllib.request.urlopen(request, timeout=6) as response:
            payload = json.loads(response.read(1024))
            return response.status == 200 and payload.get("status") == "ok"
    except (OSError, ValueError, urllib.error.URLError):
        return False


def _tunnel_event(line: str) -> str | None:
    try:
        event = json.loads(line)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(event, dict) or event.get("event") != "tunnel":
        return None
    url = event.get("url")
    if isinstance(url, str) and _URL_PATTERN.fullmatch(url):
        return url
    return None


def _run_loop(config: dict[str, Any], stop_event: Any) -> None:
    repository = config["repository"]
    _pid_file, log_file, url_file, key_file, known_hosts = _paths(config)
    _prepare_known_hosts(known_hosts)
    command = _ssh_base(key_file, known_hosts) + [
        "-n", "-T", "-R", f"80:127.0.0.1:{config.get('port', 18767)}",
        "stable@" + HOST, "output=json",
    ]
    log_file.parent.mkdir(parents=True, exist_ok=True)
    while not stop_event["stop"]:
        with log_file.open("a", encoding="utf-8", buffering=1) as log:
            log.write("[tunnl.gg] starting stable SSH reverse tunnel\n")
            child = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            stop_event["child"] = child
            url: str | None = None
            assert child.stdout is not None
            for line in child.stdout:
                log.write(line)
                if url is None:
                    candidate = _tunnel_event(line)
                    if candidate:
                        url = candidate
                        healthy = False
                        for _attempt in range(6):
                            if _health_ok(url):
                                healthy = True
                                break
                            if stop_event["stop"]:
                                break
                            time.sleep(1)
                        if healthy:
                            url_file.write_text(url + "\n", encoding="utf-8")
                            os.chmod(url_file, 0o600)
                            _publish_url(repository, url)
                            log.write("[tunnl.gg] stable URL published to private GitHub repo\n")
                        else:
                            log.write("[tunnl.gg] tunnel URL did not pass health check; reconnecting\n")
                            child.terminate()
                            break
                if stop_event["stop"]:
                    break
            if stop_event["stop"]:
                try:
                    child.terminate()
                except OSError:
                    pass
            child.wait()
            stop_event["child"] = None
        if not stop_event["stop"]:
            with log_file.open("a", encoding="utf-8") as log:
                log.write(f"[tunnl.gg] SSH exited ({child.returncode}); reconnecting in 5 seconds\n")
            stop_event["wake"].wait(5)
            stop_event["wake"].clear()


def _keepalive_loop(config: dict[str, Any], shutdown: Any) -> None:
    _pid, log_file, url_file, _key, _known = _paths(config)
    while not shutdown.wait(55 * 60):
        if not url_file.exists():
            continue
        url = url_file.read_text(encoding="utf-8").strip()
        if url and not _health_ok(url):
            with log_file.open("a", encoding="utf-8") as log:
                log.write("[tunnl.gg] keepalive health request failed; SSH reconnect loop remains active\\n")


def _worker(config_path: Path) -> None:
    config = load_config(config_path)
    import threading

    stop_event: dict[str, Any] = {
        "stop": False,
        "child": None,
        "wake": threading.Event(),
        "shutdown": threading.Event(),
    }

    def request_stop(_signum: int, _frame: Any) -> None:
        stop_event["stop"] = True
        stop_event["wake"].set()
        stop_event["shutdown"].set()
        child = stop_event.get("child")
        if child is not None:
            try:
                child.terminate()
            except OSError:
                pass

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    keepalive = threading.Thread(
        target=_keepalive_loop, args=(config, stop_event["shutdown"]), daemon=True
    )
    keepalive.start()
    _run_loop(config, stop_event)


def _matching_pid(pid_file: Path) -> int | None:
    try:
        pid = int(pid_file.read_text(encoding="ascii").strip())
        cmdline = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\x00", b" ").decode(
            "utf-8", errors="replace"
        )
        if "android_remote_bridge.tunnel" not in cmdline or "--worker" not in cmdline:
            return None
        os.kill(pid, 0)
        return pid
    except (OSError, ValueError):
        return None


def start(config_path: Path) -> str:
    config_path = config_path.expanduser().resolve()
    repository = config["repository"] if (config := load_config(config_path)) else ""
    if not _REPOSITORY_PATTERN.fullmatch(repository):
        raise TunnelError("config repository must be OWNER/PRIVATE_REPOSITORY")
    local_port = config["port"]
    if not _health_ok(f"http://127.0.0.1:{local_port}"):
        raise TunnelError(f"local Bridge is not healthy on 127.0.0.1:{local_port}")
    pid_file, log_file, url_file, key_file, known_hosts = _paths(config)
    _prepare_known_hosts(known_hosts)
    if not key_file.is_file():
        raise TunnelError(f"dedicated SSH key is missing: {key_file}; rerun installer")
    old_pid = _matching_pid(pid_file)
    if old_pid is not None:
        url = url_file.read_text(encoding="utf-8").strip() if url_file.exists() else ""
        if url and _health_ok(url):
            _publish_url(repository, url)
            return url
        raise TunnelError("tunnl.gg supervisor is already running but its URL is not healthy; inspect logs")
    log_file.parent.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(
        [sys.executable, "-m", "android_remote_bridge.tunnel", "--worker", "--config", str(config_path)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )
    os.chmod(log_file.parent, 0o700)
    pid_file.write_text(str(process.pid), encoding="ascii")
    os.chmod(pid_file, 0o600)
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        if process.poll() is not None:
            pid_file.unlink(missing_ok=True)
            raise TunnelError("tunnl.gg supervisor exited during startup; inspect tunnl.log")
        if url_file.exists():
            url = url_file.read_text(encoding="utf-8").strip()
            if _health_ok(url):
                _publish_url(repository, url)
                return url
        time.sleep(0.5)
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except OSError:
        pass
    pid_file.unlink(missing_ok=True)
    raise TunnelError("timed out waiting for a healthy tunnl.gg stable URL; inspect tunnl.log")


def stop(config_path: Path) -> bool:
    config = load_config(config_path)
    pid_file, _log_file, url_file, _key, _known = _paths(config)
    pid = _matching_pid(pid_file)
    if pid is None:
        pid_file.unlink(missing_ok=True)
        return False
    try:
        os.killpg(pid, signal.SIGTERM)
    except OSError as exc:
        raise TunnelError("could not stop the recorded tunnl.gg supervisor") from exc
    pid_file.unlink(missing_ok=True)
    url_file.unlink(missing_ok=True)
    _delete_published_url(config["repository"])
    return True


def status(config_path: Path) -> dict[str, Any]:
    config = load_config(config_path)
    pid_file, _log_file, url_file, _key, _known = _paths(config)
    pid = _matching_pid(pid_file)
    url = url_file.read_text(encoding="utf-8").strip() if url_file.exists() else None
    return {"provider": "tunnl.gg", "running": pid is not None, "pid": pid, "url": url}


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage this user's tunnl.gg SSH reverse tunnel")
    parser.add_argument("action", nargs="?", choices=("start", "stop", "status", "register"))
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        if args.worker:
            _worker(args.config)
        elif args.action == "start":
            print(start(args.config))
        elif args.action == "stop":
            print("stopped" if stop(args.config) else "not running")
        elif args.action == "register":
            register(args.config)
            print("registration session closed")
        else:
            print(json.dumps(status(args.config), ensure_ascii=False))
    except TunnelError as exc:
        parser.exit(1, f"android-remote-bridge-tunnel: {exc}\n")


if __name__ == "__main__":
    main()
