FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    cron \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data and logs directories with proper permissions
RUN mkdir -p /app/data /app/logs && \
    chown -R appuser:appuser /app

# Setup cron (needs root, will run separately)
COPY crontab /etc/cron.d/refresh-cron
RUN chmod 0644 /etc/cron.d/refresh-cron && \
    crontab /etc/cron.d/refresh-cron && \
    touch /var/log/cron.log

# Expose Streamlit port
EXPOSE 8501

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Start script
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Labels for container metadata
LABEL org.opencontainers.image.title="AI Content Curator"
LABEL org.opencontainers.image.description="Automated content curation based on interests"
LABEL org.opencontainers.image.version="1.0.0"

CMD ["/start.sh"]
