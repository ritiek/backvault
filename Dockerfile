FROM python:3.13-slim-bookworm

# Pin version for Bitwarden CLI
ARG BW_VERSION="2025.10.0"
ARG SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/v0.2.39/supercronic-linux-arm64
ARG SUPERCRONIC_SHA1SUM=5ef4ccc3d43f12d0f6c3763758bc37cc4e5af76e
ARG SUPERCRONIC=supercronic-linux-arm64

# Install minimal required packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    bash \
    unzip \
    sqlcipher \
    libssl-dev \
    libsqlite3-dev \
    libsqlcipher-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js from NodeSource repository for latest version
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# Create non-root user
RUN groupadd -g 1000 backvault \
 && useradd -m -u 1000 -g 1000 -s /bin/bash backvault

# Install Bitwarden CLI using npm (with newer Node.js version)
RUN set -eux; \
    echo "Installing Bitwarden CLI version: ${BW_VERSION} with Node.js $(node --version)"; \
    npm install -g @bitwarden/cli@${BW_VERSION}; \
    bw --version

RUN curl -fsSLO "$SUPERCRONIC_URL" \
 && echo "${SUPERCRONIC_SHA1SUM}  ${SUPERCRONIC}" | sha1sum -c - \
 && chmod +x "$SUPERCRONIC" \
 && mv "$SUPERCRONIC" "/usr/local/bin/${SUPERCRONIC}" \
 && ln -s "/usr/local/bin/${SUPERCRONIC}" /usr/local/bin/supercronic

# Prepare working directories
RUN mkdir -p /app/logs /app/backups /app/db /app/src && \
    chmod -R 700 /app && \
    chown -R 1000:1000 /app

# Copy project files
WORKDIR /app

COPY --chown=1000:1000 ./requirements.txt /app/requirements.txt
COPY --chown=1000:1000 ./src /app/src
COPY --chown=1000:1000 ./entrypoint.sh /app/entrypoint.sh
COPY --chown=1000:1000 ./cleanup.sh /app/cleanup.sh

RUN chmod +x /app/entrypoint.sh /app/cleanup.sh

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-input --no-cache-dir -r requirements.txt

RUN apt-get remove curl unzip binutils -y

ENV PYTHONPATH=/app

USER 1000:1000

ENTRYPOINT ["/app/entrypoint.sh"]
