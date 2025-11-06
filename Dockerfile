FROM python:3.12-slim-bookworm

# Install required system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    unzip \
    bash \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Install Bitwarden CLI
RUN set -eux; \
    curl -Lo bw.zip "https://bitwarden.com/download/?app=cli&platform=linux"; \
    unzip bw.zip -d /usr/local/bin; \
    chmod +x /usr/local/bin/bw; \
    rm bw.zip

# Create backup directory
RUN mkdir -p /app/backups && \
    mkdir -p /var/log/cron

# Copy application files
COPY ./src /app

# Set permissions for cron log
RUN touch /var/log/cron.log && \
    chmod 644 /var/log/cron.log

WORKDIR /app

# Set up cron job
RUN echo "0 */${BACKUP_INTERVAL_HOURS:-12} * * * /usr/bin/python3 /app/run.py >> /var/log/cron.log 2>&1" | crontab -

# Start cron in the foreground
CMD ["cron", "-f"]
