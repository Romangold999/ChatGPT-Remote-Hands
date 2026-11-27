# Security policy and secret-handling rules

## Public repository: never store secrets

This repository is public and must contain only generic source code, clean templates, documentation and tests. Never commit or upload:
- GitHub PATs, OAuth credentials, cookies or OIDC JWTs;
- passwords, HMAC secrets, SSH private keys or tunnel credentials;
- personal configuration files, personal tunnel URLs, logs or command results;
- user-specific identifiers or data copied from a reference installation.

Do not put real-looking credentials in examples. Use clearly fake placeholders only. Secret scanning and a pre-publication audit are required before releases.

## Per-user installation

- Bootstrap generates unique keys and local secrets on the user's Android device.
- The SSH private key remains local; only the public key may be registered with a tunnel provider.
- GitHub CLI stores its own authentication locally. Never print or export its credential.
- Local secret files must be excluded from Git and protected with restrictive permissions (0600 where applicable).
- Each user gets a separate private operational repository. Keep it free of private keys, PAT/OAuth credentials, HMAC secrets and long-lived bearer tokens.
- GitHub Actions obtains a short-lived OIDC token for each run; do not persist it as a repository secret.

## Termux plugins

- Termux:API is optional. If Android API features are enabled, install both the Termux:API Android plugin and the `termux-api` CLI package inside Termux.
- Termux:Boot is optional and opt-in only. Never create boot scripts, enable wake locks or configure automatic startup without explicit user consent.
- Termux and all plugins must come from the same signing source. Do not mix F-Droid and GitHub APK builds.

## Runtime security

- Use least-privilege GitHub Actions permissions.
- OIDC validation must verify signature, issuer, audience, repository, ref, timestamps and replay protection.
- Never trust decoded JWT claims without signature verification.
- Redact secrets from stdout, stderr, logs and diagnostics.
- Restrict shell execution; use explicit safe mode/allowlist by default.
- Require explicit user approval for destructive or high-risk operations.
- Do not expose the local listener directly to the public internet; use the configured tunnel.
- Pin third-party Actions to immutable commit SHAs.
- Keep mailbox concurrency serialized.
- Explain that user auth can be revoked; no credential is guaranteed forever.
- Android background execution and third-party tunnel availability are not guaranteed.
