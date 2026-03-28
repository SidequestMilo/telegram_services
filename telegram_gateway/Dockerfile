FROM python:3.11-slim

# Set working directory
WORKDIR /app

# No system build dependencies needed - all packages use pre-built wheels

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app ./app

# Create non-root user and data directory
RUN useradd -m -u 1000 telegram && \
    mkdir -p /app/data && \
    chown -R telegram:telegram /app

USER telegram

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Run the application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
