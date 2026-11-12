# syntax=docker/dockerfile:1
# Dossier Builder — cloud image. Build from the REPOSITORY ROOT:
#   docker build -f apps/dossier-builder/deploy/Dockerfile -t dossier-builder .
# (needs the EG provisional profiles + the ICH v4 XSD package from docs/ctd/, kept at the same relative paths)
ARG BASE=ubuntu:24.04
FROM ${BASE}
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-venv ca-certificates \
      libreoffice-writer-nogui fonts-noto-core fonts-dejavu-core \
      ghostscript libxml2-utils pngquant \
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
COPY docs/ctd/sources/ectd/ICH_eCTD_v4.0_IG_v1.7_with_XSD.zip docs/ctd/sources/ectd/
RUN useradd --system --uid 10001 --home-dir /data app && mkdir -p /data && chown app /data
USER app
ENV DB_MODE=cloud DB_WORKSPACE=/data PORT=8765 HOME=/data
VOLUME ["/data"]
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8765/api/health')" || exit 1
CMD ["python", "apps/dossier-builder/tools/serve.py"]
