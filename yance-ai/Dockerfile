FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
WORKDIR /build
COPY pyproject.toml requirements.txt constraints-release.txt ./
COPY app ./app
RUN python -m venv /opt/venv && /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install -c constraints-release.txt .

FROM python:3.12-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# The runtime uses /opt/venv. Remove the base image's unused pip and its
# stale vendored libraries; the builder retains its own package manager.
RUN /usr/local/bin/python -m pip uninstall --yes pip

# WeasyPrint system dependencies, Chinese fonts and local OCR runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0 \
    libffi8 libgdk-pixbuf-2.0-0 shared-mime-info \
    fonts-noto-cjk tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system yance && useradd --system --gid yance --home /app yance
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY scripts ./scripts
COPY evals ./evals
# pip's own vendored dependency tree is independent of application constraints.
# Serving containers do not install packages; remove both copies and bundled
# bootstrap wheels after the virtual environment has been assembled.
RUN /opt/venv/bin/python -m pip uninstall --yes pip \
    && rm -rf /usr/local/lib/python3.12/ensurepip \
    && mkdir -p /app/invoices && chown -R yance:yance /app
USER yance
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
