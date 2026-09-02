"""Tests for the render MCP server wiring.

Verifies the server registers ``render_html_to_pdf`` with a sane schema and
that a missing source surfaces as an MCP error. WeasyPrint is imported lazily
inside the op, so these run without the native pango/cairo libs (a real render
is the integration suite's job against the live sidecar).
"""

from __future__ import annotations

import pytest

from src import server


@pytest.mark.asyncio
async def test_render_tool_is_registered() -> None:
    names = {t.name for t in await server.mcp.list_tools()}
    assert "render_html_to_pdf" in names


@pytest.mark.asyncio
async def test_render_tool_schema_requires_src() -> None:
    tools = await server.mcp.list_tools()
    tool = next(t for t in tools if t.name == "render_html_to_pdf")
    props = tool.inputSchema["properties"]
    assert "src" in props and "dst" in props and "stylesheet" in props
    assert "src" in tool.inputSchema.get("required", [])


def test_missing_source_raises(tmp_path) -> None:
    from src.render_ops import RenderError

    with pytest.raises(RenderError, match="source not found"):
        server.render_html_to_pdf(str(tmp_path / "absent.html"))
