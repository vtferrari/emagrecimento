# Multi-arch: supports x86_64 and ARM64 (Raspberry Pi 5)
FROM python:3.10-slim

WORKDIR /app

# Install production dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY src/ src/
COPY templates/ templates/
COPY static/ static/

EXPOSE 5000

ENV PORT=5000

# Gunicorn: 2 workers, bind to all interfaces for container networking
# PORT is configurable via environment for flexibility
CMD gunicorn -w 2 -b 0.0.0.0:${PORT} app:app
