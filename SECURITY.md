# Security policy

## Credentials this project uses

- **Apple ID password** — typed into a terminal by `icloud-docs-mcp login`. Optional `ICLOUD_PASSWORD` is supported and discouraged.
- **Session cookiejar** — stored under `$XDG_DATA_HOME/icloud-docs-mcp/` (or `~/.local/share/icloud-docs-mcp/` if that variable is unset). A cookiejar is equivalent to being logged in.
- **`.env`** — gitignored. Copy `.env.example` locally. Never commit a filled-in file.

Do not attach cookiejars, `.env` files, passwords, or 2FA codes to issues, pull requests, or logs.

## Reporting a vulnerability

Do not open a public issue for credential leaks, auth bypasses, or anything that includes secrets.

1. Use GitHub's private vulnerability reporting on this repository if it is enabled, or
2. Open a draft security advisory.

Include reproduction steps and affected versions. Redact Apple IDs if you can.

## Scope

**In scope:** path handling, secret handling, MCP tool output, and session-file permissions in this repository.

**Out of scope:** Apple's iCloud service, bugs in [pyicloud](https://github.com/picklepete/pyicloud), and a compromised local machine.

## Runtime notes

- The MCP server is stdio-only. Do not bind it to HTTP or share one session across users.
- Tools are read-only (list, search, download, extract). They do not upload, rename, or delete Drive files.
- Session and download directories are created with mode `0700` when the filesystem allows it. A cookiejar is equivalent to being logged in.
- `status` returns the configured username and local directories. That is intentional and is not a password leak.
