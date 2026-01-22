FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /app/data

# Setup cron
COPY crontab /etc/cron.d/refresh-cron
RUN chmod 0644 /etc/cron.d/refresh-cron && \
    crontab /etc/cron.d/refresh-cron && \
    touch /var/log/cron.log

# Expose Streamlit port
EXPOSE 8501

# Start script
COPY start.sh /start.sh
RUN chmod +x /start.sh

CMD ["/start.sh"]
