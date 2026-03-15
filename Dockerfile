# AI-CORE – Railway / production
FROM python:3.11-slim

WORKDIR /app

# Copy dependency list first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway sets PORT at runtime; default 8000 for local runs
EXPOSE 8000
CMD uvicorn apps.orchestrator.main:app --host 0.0.0.0 --port ${PORT:-8000}
