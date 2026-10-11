# ==============================================================================
# Dockerfile: Asisten Tutor Online UT MKWN4108
# Dosen/Tutor: Ainur Rosyidah Azmie Putry, S.Pd., M.Pd.
# ==============================================================================

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=8020

WORKDIR /app

# Install system dependencies & Chromium dependencies for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies first (for optimal Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium browser and system dependencies
RUN playwright install --with-deps chromium

# Copy application source code
COPY . .

# Expose port 8020
EXPOSE 8020

# Run dashboard on port 8020
CMD ["python", "run_dashboard.py", "--host", "0.0.0.0", "--port", "8020"]
