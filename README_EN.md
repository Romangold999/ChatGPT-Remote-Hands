# ChatGPT Remote Hands

<p align="center">
  <strong>Give ChatGPT hands to work with your Android device.</strong><br>
  <sub>A personal bridge between ChatGPT and Android through Termux.</sub>
</p>

<p align="center">
  <a href="README.md">Русская версия</a>
</p>

<p align="center">
  <img alt="Platform" src="https://img.shields.io/badge/platform-Android%20%7C%20Termux-3DDC84?logo=android&logoColor=white">
  <img alt="Integration" src="https://img.shields.io/badge/integration-ChatGPT-10A37F">
  <img alt="Status" src="https://img.shields.io/badge/status-experimental-orange">
</p>

> **Status: experimental.** The push-bridge architecture and shell executor are being aligned with the user's working Termux Push Bridge. A clean Android installation and complete end-to-end validation are still required. Do not run the experimental installer over an existing working Bridge.

## What it is

ChatGPT Remote Hands is an independent open-source project connecting ChatGPT to a personal Android device through Termux, GitHub Actions, and a tunnl.gg reverse SSH tunnel.

The Bridge executes full Bash commands as the Termux app user. Commands can use files, directories, Git, Python, Node.js, and other tools installed in Termux, within Android app permissions. It is not root access or a remote desktop.

## How it works

1. GPT writes a command to mailbox/command.json in the user's private GitHub repository.
2. A push starts GitHub Actions. The workflow obtains a short-lived OIDC JWT and sends only an event containing repository, ref, commit SHA, and timestamp through the HTTPS tunnel.
3. Termux verifies the token and event, fetches the command at the exact commit SHA, and runs bash -lc with a timeout.
4. Termux writes stdout, stderr, exit code, and status to mailbox/result.json and acknowledges the command.
5. GPT reads the result and may submit the next command in a new push event.

**Termux does not poll GitHub for commands.** A new command arrives only through a GitHub Actions push event and tunnl.gg. HTTP 202 means the event was accepted, not that execution has finished.

## Capabilities

- Full shell execution in the Termux environment.
- stdout, stderr, exit code, and timeouts up to 3600 seconds.
- File operations and use of installed Termux tools.
- GitHub Actions OIDC validation: RS256, issuer, audience, repository, ref, event_name, time claims, and jti replay protection.
- Fetch commands at the exact event commit SHA.
- Persistent replay and sequence protection.
- Result publication by Termux to the private mailbox.
- Stable tunnl.gg URL, reconnect, SSH keepalive, and health ping.
- Separate private operational repository and dedicated Ed25519 key per installation.
- Installer for native Termux ARM64.

## Security

Full shell access means real command authority over files and programs available to Termux. The operational repository must remain private. Anyone with write access to mailbox/command.json effectively has the ability to execute commands on the device.

GitHub Actions only forwards the event. Termux uses its local GitHub CLI authorization to fetch commands and publish results. The GitHub credential is not copied into Bridge config, webhook requests, or the public repository. OIDC tokens are short-lived and verified for each incoming event.

Each installation creates its own tunnl.gg SSH key. The private key stays on Android.

See [SECURITY.md](SECURITY.md), [command protocol](docs/COMMAND_PROTOCOL.md), and [tunnel guide](docs/TUNNEL.md).

## Before installation

The project remains experimental. A clean Termux ARM64 installation, GitHub authorization, private repository creation, tunnel registration, and the complete command-to-result flow must be validated before release.

See [Getting Started](docs/GETTING_STARTED.md).

## Limitations

- Commands run with Termux app permissions; no root access is provided.
- Android may stop background processes; 24/7 availability is not guaranteed.
- The free tunnl.gg tier has traffic, idle, and session limits.
- tunnl.gg terminates TLS at its edge; this is not end-to-end encryption to the phone.
- ChatGPT needs a channel that can write commands to the private repository and read results. The GitHub connector may be read-only.
- A successful workflow run or HTTP 202 does not prove command completion; inspect result.json.

## Independence

This is an independent open-source project. **It is not an official OpenAI product and is not endorsed by OpenAI.**
