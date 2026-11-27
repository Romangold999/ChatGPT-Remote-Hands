# Security policy and secret-handling rules

## Public repository

This public repository may contain only generic source code, clean templates, documentation and tests. Never commit:
- GitHub PATs, OAuth credentials, cookies or OIDC JWTs;
- passwords, HMAC secrets, SSH private keys or tunnel credentials;
- personal configuration files, private tunnel URLs, logs or command results;
- user-specific identifiers or data copied from a reference installation.

## Per-user installation

- Each installation has its own private operational repository.
- GitHub CLI credentials are stored by GitHub CLI on the device. Bridge obtains the credential in memory with gh auth token; it is not copied into the Bridge config or logged.
- Every installation generates a dedicated Ed25519 key. Its private key never leaves Android.
- Local config and replay state are outside Git and use restrictive permissions.
- GitHub Actions obtains a short-lived OIDC JWT for each push event. The JWT is not persisted as a repository secret.
- The private operational repository must remain private. Any account or integration with write access to mailbox/command.json has the ability to execute shell commands as the Termux user.

## Runtime security

- OIDC validation verifies RS256 signature, issuer, audience, exact repository, exact ref, push event type, time claims and required jti.
- The event includes an exact commit SHA. Termux fetches the command from that SHA rather than trusting a mutable branch head.
- Replay protection and sequence checks are persisted locally.
- Commands are serialized; a second command is rejected while one is running.
- Shell execution is intentionally full-featured and runs as the Termux user. It is not a sandbox and does not provide privilege escalation beyond Android/Termux permissions.
- Treat write access to the private mailbox as device command authority. Protect the GitHub account and connected ChatGPT integration accordingly.
- Do not expose the listener directly to the internet; use the pinned tunnl.gg SSH reverse tunnel.
- /health returns no configuration or device details.
- Pin third-party Actions to immutable commit SHAs.
- Redact credentials from logs and diagnostics.

## Optional Android integration

- Termux:API is optional and requires both the Android plugin and the Termux CLI package.
- Termux:Boot is optional and must be explicitly enabled by the user; never install or enable it silently.
- Termux and plugins must come from the same signing source.

## Service limitations

- Android may stop background processes; 24/7 availability is not guaranteed.
- The free tunnl.gg tier has service-side limits (idle timeout, maximum session length, traffic and concurrent tunnels).
- tunnl.gg terminates TLS at its edge; do not treat it as end-to-end encryption to the device.
- Users can revoke GitHub CLI authorization or remove repository access at any time.

Report security issues privately to the repository owner. Do not publish credentials or exploit details in public issues.
