# Changelog

## Unreleased

- README banner (`docs/banner.jpg`).
- Session and download directories are created with mode `0700`.
- Positioned as a cross-platform Drive utility (no Mac required), not a hosted product. Unofficial `pyicloud` reliability is called out as a hard limit.

## 0.1.0

- Initial public release: read-only iCloud Drive MCP server.
- Tools: `status`, `list_folder`, `search`, `download`, `read_text`.
- Interactive `icloud-docs-mcp login` for Apple ID + 2FA; MCP tools never prompt.
- Sessions stored in XDG data directories; credentials stay out of the repo.
- Public GitHub repo: [js713-lab/icloud4u-mcp](https://github.com/js713-lab/icloud4u-mcp).
- MCP registry metadata in `server.json` (`io.github.js713-lab/icloud-docs-mcp`).
- Grok/Claude plugin stub in `.mcp.json`.
- GitHub Release MCPB listing for the official MCP Registry (see `PUBLISH.md`).
