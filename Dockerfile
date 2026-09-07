# Toolspace sidecar (render): a per-chat co-located helper container that owns
# WeasyPrint and exposes HTML→PDF rendering as an MCP tool over Streamable HTTP
# (http://localhost:8095/mcp). The workspace agent calls it instead of running
# WeasyPrint itself — letting the workspace main image shed WeasyPrint's native
# render stack (pango/cairo/gdk-pixbuf + font packages).
#
# Mirrors apps/workspace-tools/office (the "orbital workspace-tools" substrate).

FROM python:3.12-slim AS py-builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      gcc musl-dev \
  && rm -rf /var/lib/apt/lists/*

COPY workspace-tools/render/requirements.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim

# The native libs WeasyPrint links to (cairo/pango/gdk-pixbuf/ffi) plus the
# fonts so HTML→PDF renders text — including non-Latin glyphs and the
# Calibri/Cambria metric-compatible substitutes (carlito/caladea) — without
# depending on the user's system fonts. This is the stack we are concentrating
# HERE so the per-chat workspace image stays small.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates \
      libpango-1.0-0 \
      libpangoft2-1.0-0 \
      libcairo2 \
      libgdk-pixbuf-2.0-0 \
      libffi8 \
      shared-mime-info \
      fonts-dejavu \
      fonts-liberation \
      fonts-crosextra-carlito \
      fonts-crosextra-caladea \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=py-builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=py-builder /usr/local/bin /usr/local/bin

COPY workspace-tools/render/src ./src
# The one log format every tool image installs (apps/workspace-tools/toollog).
# COPY'd next to src, imported as `toollog` under `python -m` from /app — the
# same shape connector_base uses. Stdlib-only, so it adds no requirements.
COPY workspace-tools/toollog ./toollog


ENV PYTHONPATH=/app

# Mirror the workspace pod's unprivileged identity (uid/gid 65532) so PDFs
# WeasyPrint writes onto the shared tenant PVC carry the ownership the main
# container expects (fsGroup 65532). See workspace Dockerfile + the operator
# podSpec securityContext.
RUN groupadd --system --gid 65532 tool \
 && useradd --system --uid 65532 --gid 65532 --home-dir /home/tool --shell /bin/bash tool \
 && mkdir -p /home/tool \
 && chown -R tool:tool /home/tool
ENV HOME=/home/tool

EXPOSE 8095

USER tool

ENTRYPOINT ["python", "-m", "src.server"]
