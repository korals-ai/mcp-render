"""Toolspace sidecar (render) — MCP server over Streamable HTTP.

Exposes WeasyPrint HTML→PDF rendering as an MCP tool the workspace agent calls
over ``http://localhost:8095/mcp`` (the containers share the pod network
namespace). Moves WeasyPrint + its native render stack (pango/cairo/gdk-pixbuf
+ fonts) out of the per-chat workspace image; the agent authors HTML on the
shared tenant PVC, names the path, and this sidecar writes the PDF back in
place (zero-copy data plane).

Transport is Streamable HTTP (not stdio) because the server lives in a separate
container from the agent. The tool surface IS the agent-facing contract.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

import loopwatch
import toollog
from mcp.server.fastmcp import FastMCP

from src import render_ops
from src.render_ops import RenderError

log = logging.getLogger("workspace-tool-render")

HOST = "0.0.0.0"  # noqa: S104 - pod-local bind; nothing injects a host, the pod netns is the fence
PORT = int(os.environ["WORKSPACE_TOOL_PORT"])

mcp = FastMCP("render", host=HOST, port=PORT, lifespan=loopwatch.lifespan)


@mcp.tool()
def render_html_to_pdf(src: str, dst: str | None = None, stylesheet: str | None = None) -> str:
    """Render an HTML file to a PDF — the way to produce a polished tender
    deliverable (proposal, BOM, cover letter) from HTML/CSS you authored.

    Relative URLs in the HTML (images, stylesheets) resolve against the source
    file's directory on the shared volume, so reference sibling assets you wrote
    there.

    Args:
        src: Absolute path to the source ``.html`` on the shared workspace volume.
        dst: Optional output path; defaults to ``<src-stem>.pdf`` next to src.
        stylesheet: Optional absolute path to an extra CSS file to apply.

    Returns: the absolute path of the written PDF.

    Raises: an MCP tool error (with the WeasyPrint message) on a missing source
    or a render failure.
    """
    started = time.monotonic()
    try:
        out = render_ops.render_html_to_pdf(src, dst=dst, stylesheet=stylesheet)
    except RenderError as exc:
        log.warning(
            "tool=render op=html_to_pdf outcome=error dur_ms=%d src=%s err=%s",
            int((time.monotonic() - started) * 1000),
            Path(src).name,
            exc,
        )
        raise
    log.info(
        "tool=render op=html_to_pdf outcome=ok dur_ms=%d src=%s",
        int((time.monotonic() - started) * 1000),
        Path(src).name,
    )
    return out


def main() -> None:
    """Run the MCP server forever over Streamable HTTP. Blocks; entrypoint."""
    toollog.configure("render")
    log.info("workspace-tool-render MCP server on %s:%d (/mcp)", HOST, PORT)
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
