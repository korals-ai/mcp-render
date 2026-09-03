"""HTML→PDF rendering for the workspace-tool-render sidecar.

Wraps WeasyPrint to turn an HTML file on the shared tenant PVC into a PDF in
place — the agent authors ``proposal.html`` (with CSS + images on the volume),
calls this, and gets ``proposal.pdf`` back. Only the path + verdict cross the
MCP wire (zero-copy data plane, mirroring the office/ocr/cad/ffmpeg sidecars).

Moves WeasyPrint *and its native render stack* (pango/cairo/gdk-pixbuf + the
font packages) out of the per-chat workspace image. ``weasyprint`` is imported
lazily inside the call so this module (and the MCP server) load without the
native libraries present — the registration tests run anywhere; only a real
render needs the libs (which the sidecar image carries).
"""

from __future__ import annotations

from pathlib import Path


class RenderError(Exception):
    """An HTML→PDF render failed. Carries a human-readable message."""


def render_html_to_pdf(src: str, dst: str | None = None, stylesheet: str | None = None) -> str:
    """Render an HTML file to PDF with WeasyPrint.

    Relative URLs in the HTML (``<img src=...>``, ``<link rel=stylesheet>``)
    resolve against the source file's directory on the shared volume, so the
    agent can reference sibling assets it wrote there.

    Args:
        src: Absolute path to the source ``.html`` on the shared volume.
        dst: Optional output path; defaults to ``<src-stem>.pdf`` next to src.
        stylesheet: Optional absolute path to an extra CSS file to apply.

    Returns: the absolute path of the written PDF.
    """
    source = Path(src)
    if not source.is_file():
        raise RenderError(f"source not found: {source}")
    out = Path(dst) if dst else source.with_suffix(".pdf")

    # Lazy import: keeps the module importable without pango/cairo present.
    try:
        from weasyprint import CSS, HTML
    except ImportError as exc:  # pragma: no cover - only when native libs absent
        raise RenderError(f"WeasyPrint unavailable: {exc}") from exc

    stylesheets = [CSS(filename=stylesheet)] if stylesheet else None
    try:
        HTML(filename=str(source)).write_pdf(str(out), stylesheets=stylesheets)
    except Exception as exc:  # weasyprint raises a variety of errors on bad input
        raise RenderError(f"render failed: {exc}") from exc
    return str(out)
