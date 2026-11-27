# ChatGPT Remote Hands

<p align="center">
  <strong>Give ChatGPT hands to work with your Android device.</strong><br>
  <sub>A personal, security-focused bridge between ChatGPT and Android through Termux.</sub>
</p>

<p align="center">
  <a href="README.md">Русская версия</a>
</p>

<p align="center">
  <img alt="Platform" src="https://img.shields.io/badge/platform-Android%20%7C%20Termux-3DDC84?logo=android&logoColor=white">
  <img alt="Integration" src="https://img.shields.io/badge/integration-ChatGPT-10A37F">
  <img alt="Status" src="https://img.shields.io/badge/status-experimental-orange">
</p>

> **Important: this project is experimental and still under development.** Automated unit tests pass, but a clean Android installation and the complete “ChatGPT → phone → result” flow have not yet been verified. Do not run the installer on your primary device until the beginner guide explicitly marks it ready.

## What is it?

ChatGPT Remote Hands is an independent open-source project intended to let ChatGPT send approved operations to your own Android device and receive their results through Termux.

It is **not** a remote desktop or unrestricted phone-control tool. The current Bridge supports only a small allowlist of built-in operations; arbitrary shell commands are not supported.

## How it is intended to work

1. Install Termux on your Android device.
2. Run the one-command installer to prepare the local Bridge and your personal private GitHub repository.
3. GitHub Actions obtains a short-lived OIDC token and forwards a request through your own HTTPS tunnel.
4. The Bridge validates the request, runs an approved operation, and returns a structured result.
5. The workflow publishes that result to your private mailbox for ChatGPT to read through a channel with the required access.

Each user has their own phone, private repository, SSH key, and tunnel. The project does not operate a shared command server for all users.

## Is it ready to install?

**Not yet.** The current installer exists, but it has not passed a complete clean-device test on Android/Termux ARM64. The one-command flow is the target for beginners; it must not be presented as production-ready until that test succeeds.

The repository currently includes:
- a local Termux Bridge runtime;
- GitHub Actions OIDC token validation and replay protection;
- three built-in operations: `bridge.status`, `bridge.health`, and `system.info`;
- a private operational repository template and GitHub Actions workflow;
- an SSH reverse-tunnel manager using tunnl.gg;
- an experimental ARM64 Termux installer;
- automated project tests.

Before public release, we still need to verify a clean installation, the full end-to-end command/result flow, recovery after interruptions, and a real ChatGPT integration channel with both write and read access.

## Start here

- [Beginner installation guide](docs/GETTING_STARTED.md) — Termux download, GitHub sign-in note, the visible one-command installer, and required browser confirmations.
- [Download the ChatGPT instruction prompt (.md)](CHATGPT_PROMPT_RU.md?raw=1) — a Markdown file describing the Bridge's real capabilities, limits, and safe operating rules.

The installer command in the guide is explicitly marked **do not run yet** until clean-device testing is complete.

## Important integration limitation

The ChatGPT GitHub connector may be read-only. A read-only connection cannot submit commands to the private repository. A working two-way setup requires a channel that can write a command and read its result. Do not assume that merely connecting GitHub to ChatGPT enables device control.

## Security and privacy

- Every user has a separate installation and private GitHub repository.
- Private SSH keys and local secrets are generated on the Android device and must never be published.
- The public repository contains source code, documentation, tests, and clean templates only.
- The Bridge validates GitHub Actions OIDC tokens and accepts only explicitly allowlisted operations.
- The current operational workflow needs `contents: write` to publish the result mailbox and `id-token: write` to request a short-lived OIDC token.

Never post tokens, passwords, private keys, local configuration, or personal tunnel URLs in public Issues or Discussions. See [SECURITY.md](SECURITY.md).

## Known limitations

- Android may stop background processes; 24/7 operation is not guaranteed.
- The free tunnl.gg tier has session, idle-time, and traffic limits.
- A successful workflow run or HTTP response alone is not enough; the actual result mailbox must be checked.
- The tunnel provider terminates TLS at its edge; do not treat it as end-to-end encryption to the phone.
- This is an independent open-source project. **It is not an official OpenAI product and is not endorsed by OpenAI.**

## Development documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Installation plan](docs/INSTALLATION_PLAN.md)
- [Command protocol](docs/COMMAND_PROTOCOL.md)
- [GitHub authorization and OIDC](docs/GITHUB_AUTH.md)
- [Tunnel setup](docs/TUNNEL.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Roadmap](docs/ROADMAP.md)
- [Security model](SECURITY.md)
- [Contributing](CONTRIBUTING.md)

---

<p align="center">
  <sub>ChatGPT Remote Hands — your Android, your Bridge, your keys, your rules.</sub>
</p>
