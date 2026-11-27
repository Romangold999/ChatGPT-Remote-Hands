# Per-user operational repository

This directory is a clean template. The installer copies it into a **new private
repository owned by the individual user**. Never commit a real user's tunnel
URL, tokens, keys, credentials, local config or execution output to this public
template.

## Required per-user setting

Create the repository Actions variable:

- `BRIDGE_TUNNEL_URL`: this user's current HTTPS tunnel base URL.

The Android listener must be configured with the matching values:

- audience: `termux-bridge`
- repository: the exact private repository name, `OWNER/REPOSITORY`
- ref: `refs/heads/main`

The workflow requests a fresh GitHub Actions OIDC token for every run. It sends
the command envelope to the configured user's tunnel, then publishes the
structured result to `mailbox/result.json`.

The workflow does not make arbitrary shell commands available. The Android
listener validates the envelope and executes only its local allowlist.

## Important

- This is a template, not a shared service.
- Every installation must get its own private repository and tunnel.
- Do not enable broad write permissions beyond the workflow's mailbox result
  commit requirement.
- A successful workflow run is not enough: inspect the result object's
  `status`, `id` and `sequence`.
- Only one mailbox command may be in flight at a time.
