# Publish icloud-docs-mcp

The official MCP Registry listing for `io.github.js713-lab/icloud-docs-mcp` is an **MCPB** on the GitHub release. PyPI is optional and separate.

Keep this comment in `README.md` if you later add a PyPI package:

```html
<!-- mcp-name: io.github.js713-lab/icloud-docs-mcp -->
```

## Current release path (MCPB)

1. Bump `version` in `pyproject.toml`, `manifest.json`, and `server.json`.
2. Pack and hash:

```bash
npx -y @anthropic-ai/mcpb pack
sha256sum icloud-docs-mcp.mcpb
```

3. Put the SHA-256 into `server.json` `packages[0].fileSha256` and the release URL into `identifier`.
4. Commit, tag `v0.1.0`, attach `icloud-docs-mcp-0.1.0.mcpb` to the GitHub release.
5. `mcp-publisher login github && mcp-publisher publish`

Registry versions are immutable. A metadata fix is a new version + a new tag.

## Optional later: PyPI

Create a [pending trusted publisher](https://pypi.org/manage/account/publishing/) for project `icloud-docs-mcp`, owner `js713-lab`, repository `icloud4u-mcp`, workflow `publish-mcp.yml`. Then run the workflow from the Actions tab.
