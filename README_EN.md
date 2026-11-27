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

> **Important: this project is still under development.** The core runtime and an initial installer exist, and automated tests pass, but a clean Android installation and the complete “ChatGPT → phone → result” flow have not yet been verified. Do not treat this repository as a ready-to-use app or run the installer on your primary device yet.

## What is it?

ChatGPT Remote Hands is an experimental project intended to let ChatGPT send approved operations to your own Android device and receive their results.

It is **not** a remote desktop or unrestricted phone-control tool. The Bridge is designed to execute only explicitly allowlisted operations, not arbitrary shell commands.

## How it is intended to work

1. Install Termux and your personal Bridge on your Android device.
2. Create your own private GitHub repository for command and result exchange.
3. GitHub Actions validates a request and forwards it through a secure tunnel to your phone.
4. The Bridge validates the request, performs an approved operation, and returns the result.
5. ChatGPT receives the result through an integration channel that supports the required read and write access.

Each user has their own phone, private repository, keys, and tunnel. There is no shared central project server handling every user's commands.

## Who is it for?

The project is being built primarily for **ChatGPT users** who want to connect the assistant to their own Android device.

There is an important requirement: the ChatGPT integration method must actually be able to write requests to the private repository and read results. The GitHub connector in ChatGPT may be read-only. Having that connector available does not automatically mean it can operate the Bridge.

## Is it ready to install?

**Not yet.** We do not want beginners to have to understand source code or assemble the system manually from many components.

The repository currently includes:
- a local Termux Bridge runtime;
- GitHub OIDC token validation and replay protection;
- a limited allowlist of built-in operations;
- a private operational repository template and GitHub Actions workflow;
- an SSH reverse-tunnel manager using tunnl.gg;
- an initial installer for Termux on ARM64;
- automated project tests.

Before a public release, we still need to:
- verify a clean installation on Android/Termux;
- complete an end-to-end test from a ChatGPT request to a result on the phone;
- test recovery after network interruptions and restarts;
- write a beginner-friendly setup guide;
- verify a real ChatGPT integration channel with write access to the private repository.

**If you are new to this project, please do not install anything yet.** A clear “Start here” guide will be added after the installation flow is verified.

## Security and privacy

- Every user gets a separate installation and private GitHub repository.
- Private SSH keys and local secrets are generated on the device and must never be published.
- The public repository contains only source code, documentation, tests, and clean templates.
- The Bridge accepts only validated requests and allowlisted operations.
- The project is not intended to provide hidden or unrestricted access to your phone.

Never post tokens, passwords, private keys, local configuration, or personal tunnel URLs in public Issues or Discussions. See [SECURITY.md](SECURITY.md).

## Known limitations

- Android may stop background processes; 24/7 operation is not guaranteed.
- The free tunnl.gg tier has session, idle-time, and traffic limits.
- A webhook acceptance response does not mean that an operation has completed.
- A successful GitHub Actions run alone does not prove that the phone executed the operation; the result must be checked.
- This is an independent open-source project. **It is not an official OpenAI product and is not endorsed by OpenAI.**

## Development documentation

The following documentation is currently aimed at developers and testers:

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
