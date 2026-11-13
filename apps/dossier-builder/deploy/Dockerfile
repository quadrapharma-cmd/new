# syntax=docker/dockerfile:1
# Dossier Builder — cloud image. Build from the REPOSITORY ROOT:
#   docker build -f apps/dossier-builder/deploy/Dockerfile -t dossier-builder .
# (needs the EG provisional profiles + the ICH v4 XSD package from docs/ctd/, kept at the same relative paths)
ARG BASE=ubuntu:24.04

# PdfCraft — the program's PDF engine (docs/ctd/PDFCRAFT-INTEGRATION.md): built from its pinned release (tools/pdfcraft/PIN) without
# its MCP server. It needs only libc at run time.
FROM rust:1-bookworm AS pdfcraft
RUN apt-get update && apt-get install -y --no-install-recommends cmake clang git python3 && rm -rf /var/lib/apt/lists/*
COPY apps/dossier-builder/tools/pdfcraft/PIN apps/dossier-builder/tools/pdfcraft/licenses.py /tmp/
COPY apps/dossier-builder/tools/pdfcraft/patches /tmp/patches
RUN git init -q /src && cd /src && git remote add origin https://github.com/storytold/pdfcraft \
    && git fetch -q --depth 1 origin "$(cat /tmp/PIN)" && git -c advice.detachedHead=false checkout -q FETCH_HEAD \
    && test "$(git rev-parse HEAD)" = "$(cat /tmp/PIN)" \
    && for p in /tmp/patches/*.patch; do git apply --whitespace=nowarn "$p"; done \
    && cargo build --release --locked -p pdfcraft-cli --no-default-features \
    && mkdir /out && cp target/release/pdfcraft-cli LICENSE-MIT LICENSE-APACHE NOTICE ATTRIBUTION.md /out/ && cp -R licenses /out/ \
    && python3 /tmp/licenses.py /src /out && cp /tmp/PIN /out/PIN && cp /tmp/patches/*.patch /out/

FROM ${BASE}
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-venv ca-certificates \
      libreoffice-writer-nogui fonts-noto-core fonts-dejavu-core \
      ghostscript libxml2-utils pngquant \
      tesseract-ocr tesseract-ocr-ara tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
WORKDIR /srv/app
COPY apps/dossier-builder/deploy/requirements.txt /tmp/requirements.txt
# optional build secret «extra_ca» only for networks that re-sign TLS (corporate proxies); ignored otherwise
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -f /run/secrets/extra_ca ]; then export PIP_CERT=/run/secrets/extra_ca; fi; \
    pip install --no-cache-dir -r /tmp/requirements.txt
COPY apps/dossier-builder/engine apps/dossier-builder/engine
COPY apps/dossier-builder/rulepacks apps/dossier-builder/rulepacks
COPY apps/dossier-builder/ui apps/dossier-builder/ui
COPY apps/dossier-builder/tools/serve.py apps/dossier-builder/tools/adduser.py apps/dossier-builder/tools/
COPY docs/ctd/ectd/EG-PROVISIONAL-PROFILE-v0 docs/ctd/ectd/EG-PROVISIONAL-PROFILE-v0
COPY docs/ctd/ectd/EG-PROVISIONAL-PROFILE-v4-v0 docs/ctd/ectd/EG-PROVISIONAL-PROFILE-v4-v0
COPY docs/ctd/ectd/EU-M1-3.1.1-PROFILE docs/ctd/ectd/EU-M1-3.1.1-PROFILE
COPY docs/ctd/ectd/GCC-M1-1.5-PROFILE docs/ctd/ectd/GCC-M1-1.5-PROFILE
COPY --from=pdfcraft /out /opt/pdfcraft
# the text-recognition models, pinned and checked (tools/ocr/fetch.py): Tesseract's accurate Arabic and English models, and PaddleOCR's
# Arabic model — the second reader for the words Tesseract is unsure of (Apache-2.0, their licences beside them)
COPY apps/dossier-builder/tools/ocr/fetch.py /tmp/ocr-fetch.py
RUN python3 /tmp/ocr-fetch.py --out /opt/ocr && rm /tmp/ocr-fetch.py
COPY docs/ctd/sources/ectd/ICH_eCTD_v4.0_IG_v1.7_with_XSD.zip docs/ctd/sources/ectd/
RUN useradd --system --uid 10001 --home-dir /data app && mkdir -p /data && chown app /data
USER app
ENV DB_MODE=cloud DB_WORKSPACE=/data PORT=8765 HOME=/data PDFCRAFT_CLI=/opt/pdfcraft/pdfcraft-cli \
    DOSSIER_TESSDATA=/opt/ocr/tessdata DOSSIER_PADDLE_REC=/opt/ocr/paddle/arabic_PP-OCRv5_rec_mobile.onnx
VOLUME ["/data"]
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8765/api/health')" || exit 1
CMD ["python", "apps/dossier-builder/tools/serve.py"]
