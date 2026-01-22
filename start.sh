#!/bin/bash
# start.sh

# Start cron in background
cron

# Start Streamlit
exec streamlit run app.py \
    --server.address=0.0.0.0 \
    --server.port=8501 \
    --server.headless=true
