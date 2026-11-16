FROM ghcr.io/dhis2-chap/chapkit-py:latest

# chapkit-py runs as root; matches chapkit-r / chapkit-r-inla.
USER root

WORKDIR /work
# Copy lockfile + manifest first so the dep-install layer caches independently of code changes.
# Run `uv sync` once locally before the first `docker build` to generate uv.lock.
COPY pyproject.toml uv.lock ./

# Sync runtime deps (chapkit + the user's pyproject deps) into the base image's
# venv at /app/.venv. The chapkit-{py,r,r-inla}:latest images no longer ship
# chapkit pre-installed (see chapkit-images), so this step is required for the
# generated main.py to import chapkit at runtime. --frozen pins to uv.lock for
# reproducible builds, --no-dev skips dev-only deps (uvicorn etc. arrive
# transitively through chapkit), --no-install-project because this isn't a
# package, just a service.
RUN --mount=type=cache,target=/root/.cache/uv \
    UV_PROJECT_ENVIRONMENT=/app/.venv uv sync --frozen --no-dev --no-install-project

# Migrated projects ship arbitrary user files (R scripts, helper modules, config
# YAMLs, ...) at the root, so we copy the whole tree rather than enumerating
# (`COPY main.py ./` + `COPY scripts/` like the scaffold does for its known layout).
COPY . /work


EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl --fail http://localhost:8000/health || exit 1

# Run uvicorn directly so server flags (--workers, --log-level, --timeout-keep-alive,
# etc.) are visible here in the Dockerfile. main.py's `if __name__ == "__main__":`
# block stays as the local-dev shortcut for `python main.py`.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]