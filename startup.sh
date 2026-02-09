#!/bin/bash
# Azure Web App Startup Script for Streamlit
# This script is executed when the container starts

echo "Starting Octopus Agile Dashboard on Azure Web App..."

# Get the port from Azure (Azure sets the PORT environment variable)
# Default to 8000 if not set
PORT=${PORT:-8000}

echo "Streamlit will run on port: $PORT"

# Start Streamlit with Azure-specific configuration
python -m streamlit run streamlit_app.py \
  --server.port=$PORT \
  --server.address=0.0.0.0 \
  --server.headless=true \
  --server.enableCORS=false \
  --server.enableXsrfProtection=false \
  --browser.gatherUsageStats=false
