# icloud-docs-mcp

<!-- mcp-name: io.github.js713-lab/icloud-docs-mcp -->

Read-only [Model Context Protocol](https://modelcontextprotocol.io/) server for **iCloud Drive**.

Source: [js713-lab/icloud4u-mcp](https://github.com/js713-lab/icloud4u-mcp). The installable package and CLI are named `icloud-docs-mcp`.

It lists a folder, searches by filename, downloads files, and extracts text from common documents. There is no default Apple ID, no bundled documents, and no company-specific search logic.

Apple does not publish a third-party iCloud Drive API. This server uses the unofficial [`pyicloud`](https://github.com/picklepete/pyicloud) library. Apple can change endpoints without notice.

## What it is not

- Not Mail, Calendar, Contacts, or Notes
- Not a hosted / HTTP MCP (it runs locally over stdio)
- Not a 2FA prompt inside the model session
- Not upload, rename, or delete

## Disclaimer

This is not an Apple product. Apple does not publish a third-party iCloud Drive API. The unofficial client can break when Apple changes endpoints, and using it may conflict with Apple's terms. Use it at your own risk, locally, on an account you control.

Do not expose this server on the network. Cookiejar files are login credentials: never commit them, never paste them into issues, and never check in `.env`. See [SECURITY.md](SECURITY.md).

The `status` tool returns the configured Apple ID and local cache paths so a client can tell whether login succeeded. It never returns a password.

## Install

Python 3.10+

From this repository:

```bash
git clone https://github.com/js713-lab/icloud4u-mcp.git
cd icloud4u-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Install from GitHub:

```bash
pip install git+https://github.com/js713-lab/icloud4u-mcp.git
```

Or, once the package is on PyPI:

```bash
pip install icloud-docs-mcp
```

Copy `.env.example` to `.env` and set `ICLOUD_USERNAME` to your Apple ID. `.env` is gitignored.

```bash
cp .env.example .env
```

## Login (required once)

The MCP process will not wait for a 2FA code. Log in in a real terminal:

```bash
export ICLOUD_USERNAME='you@example.com'
icloud-docs-mcp login
```

You will be prompted for the password and, if Apple asks, a 6-digit device code. A trusted cookiejar is stored under:

```
$XDG_DATA_HOME/icloud-docs-mcp/<sanitized-username>/
```

(`~/.local/share/icloud-docs-mcp/...` if `XDG_DATA_HOME` is unset.)

If a tool returns `NEED_LOGIN` or `NEED_2FA`, run `icloud-docs-mcp login` again, then retry.

```bash
icloud-docs-mcp status
```

## Tools

| Tool | Purpose |
|------|---------|
| `status` | Session health. Returns the Apple ID and cache paths, never a password. |
| `list_folder` | One directory. Empty path is Drive root (or `ICLOUD_ROOT`). |
| `search` | Filename/path query, optional `ext`, capped results. |
| `download` | Copy Drive files to the local cache. Returns paths, not bytes. |
| `read_text` | Download if needed; extract text from pdf, docx, xlsx, txt, csv. |

Search and `read_text` are capped so MCP clients with a small result limit are not flooded.

## Environment

| Variable | Required | Meaning |
|----------|----------|---------|
| `ICLOUD_USERNAME` | yes | Apple ID. No default. |
| `ICLOUD_PASSWORD` | no | Login CLI prompts if unset. Avoid putting this in the MCP env. |
| `ICLOUD_SESSION_DIR` | no | Cookiejar directory override. |
| `ICLOUD_DOWNLOAD_DIR` | no | Local download cache. |
| `ICLOUD_ROOT` | no | Drive folder prefix; all tools are scoped under it. |

## MCP clients

Default command (no args) speaks MCP on stdio:

```bash
icloud-docs-mcp
```

### Grok

```toml
[mcp_servers.icloud_docs]
command = "icloud-docs-mcp"
env = { ICLOUD_USERNAME = "${ICLOUD_USERNAME}" }
startup_timeout_sec = 45
tool_timeout_sec = 180
tool_timeouts = { search = 180, download = 300, read_text = 180 }
```

### Claude Desktop / Cursor

```json
{
  "mcpServers": {
    "icloud-docs": {
      "command": "icloud-docs-mcp",
      "env": {
        "ICLOUD_USERNAME": "<your-apple-id>"
      }
    }
  }
}
```

Use an absolute path to the venv binary if the client does not inherit your `PATH`.

Grok can also load `.mcp.json` from this repo:

```bash
grok plugin install js713-lab/icloud4u-mcp --trust
```

That only starts the server. You still need `pip install icloud-docs-mcp` (or `pip install -e .`) and `icloud-docs-mcp login` on the machine.

To publish a release to PyPI and the official MCP Registry, see [PUBLISH.md](PUBLISH.md).

## Development

```bash
pip install -e ".[dev]"
pytest
```

Tests mock Apple. CI must never log into iCloud. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT. Security reports: [SECURITY.md](SECURITY.md).
