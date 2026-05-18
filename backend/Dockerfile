FROM python:3.11-slim

WORKDIR /app

# System dependencies for PostGIS / GeoPandas / Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    g++ \
    gdal-bin \
    libgdal-dev \
    python3-dev \
    libgeos-dev \
    libproj-dev \
    curl \
    wget \
    ca-certificates \
    fonts-liberation \
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium browser
RUN playwright install chromium --with-deps

# Copy application source
COPY . .

# Create non-root user
RUN useradd -m -u 1000 geoanalytica && \
    chown -R geoanalytica:geoanalytica /app
USER geoanalytica

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
