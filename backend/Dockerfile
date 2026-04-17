FROM python:3.12-slim

# System dependencies for PyMuPDF
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libmupdf-dev \
        libfreetype6-dev \
        libharfbuzz-dev \
        libjpeg62-turbo-dev \
        libopenjp2-7-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]"

# Copy application code
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
