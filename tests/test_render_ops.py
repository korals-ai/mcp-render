"""Unit tests for the render op helper.

Covers the validation + path-resolution that runs BEFORE WeasyPrint is touched
(so no native libs are needed), plus a mocked success path asserting the output
path and that the lazy WeasyPrint call is invoked.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from src import render_ops
from src.render_ops import RenderError


def test_missing_source_raises() -> None:
    with pytest.raises(RenderError, match="source not found"):
        render_ops.render_html_to_pdf("/nope/missing.html")


def test_default_output_is_pdf_next_to_source(tmp_path, monkeypatch) -> None:
    src = tmp_path / "proposal.html"
    src.write_text("<h1>hi</h1>")
    calls: dict[str, object] = {}

    # Stub a minimal weasyprint module so the lazy import inside the op succeeds
    # without the native libraries.
    class _HTML:
        def __init__(self, *, filename: str) -> None:
            calls["filename"] = filename

        def write_pdf(self, target: str, *, stylesheets=None) -> None:
            calls["target"] = target
            Path(target).write_bytes(b"%PDF-1.7")

    fake = types.ModuleType("weasyprint")
    fake.HTML = _HTML  # type: ignore[attr-defined]
    fake.CSS = lambda **_: object()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "weasyprint", fake)

    out = render_ops.render_html_to_pdf(str(src))

    assert out == str(tmp_path / "proposal.pdf")
    assert calls["filename"] == str(src)
    assert Path(out).read_bytes().startswith(b"%PDF")
