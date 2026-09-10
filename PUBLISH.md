# Publish icloud-docs-mcp

Two public artifacts, in order: **PyPI** (`icloud-docs-mcp`) then the **MCP Registry** (`io.github.js713-lab/icloud-docs-mcp`).

The registry only stores metadata. It will reject the listing unless the PyPI README still contains:

```html
<!-- mcp-name: io.github.js713-lab/icloud-docs-mcp -->
```

Do not remove that comment.

## One-time setup

1. Make [js713-lab/icloud4u-mcp](https://github.com/js713-lab/icloud4u-mcp) **public**.
2. Sign in to [pypi.org](https://pypi.org) as the publisher account.
3. Create a **pending trusted publisher** (Publishing → pending publishers):
   - PyPI project name: `icloud-docs-mcp`
   - Owner: `js713-lab`
   - Repository: `icloud4u-mcp`
   - Workflow name: `publish-mcp.yml`
   - Environment: leave empty
4. Confirm `pyproject.toml` version, `server.json` version, and `packages[0].version` match.

## Release

```bash
pytest
git tag v0.1.0
git push origin v0.1.0
```

The tag must equal the version in `pyproject.toml` (no other `v0.1.0` vs `0.1.0` mismatch). `.github/workflows/publish-mcp.yml` then builds, uploads to PyPI via OIDC, and publishes `server.json` to `registry.modelcontextprotocol.io`.

Registry versions are immutable. A metadata fix is a new version + a new tag.

## Verify

- https://pypi.org/project/icloud-docs-mcp/
- https://github.com/js713-lab/icloud4u-mcp/actions
- `curl "https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.js713-lab/icloud-docs-mcp"`
