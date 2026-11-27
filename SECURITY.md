# Security notes

- Public repository is source/template only.
- Each user operates a separate private repository.
- Never commit user PAT, OAuth token, OIDC JWT, SSH private key, HMAC secret, cookies, personal logs, command outputs or tunnel credentials.
- Use least-privilege GitHub Actions permissions.
- OIDC validation must verify signature, issuer, audience, repository, ref, timestamps and replay protection.
- Never trust decoded JWT claims without signature verification.
- Protect local config with restrictive permissions (0600 where applicable).
- Redact secrets from logs and diagnostics.
- Restrict shell execution; use explicit safe mode/allowlist by default.
- Require explicit user approval for destructive or high-risk operations.
- Do not expose the local listener directly to the public internet; use the configured tunnel.
- Pin third-party Actions to immutable commit SHAs.
- Keep concurrency serialization for mailbox.
- Explain that long-lived user auth can be revoked; no credential is guaranteed forever.
- Android background execution and third-party tunnel availability are not guaranteed.
