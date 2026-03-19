FROM python:3.12-slim

WORKDIR /backend

# asyncpg requires gcc to compile its C extension
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Install dependencies first (cached unless pyproject.toml changes)
COPY pyproject.toml .
RUN mkdir -p app && touch app/__init__.py && \
    pip install --no-cache-dir . && \
    rm -rf app

# Copy application code
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
