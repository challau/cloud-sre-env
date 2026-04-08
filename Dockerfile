# Root Dockerfile — for Hugging Face Spaces (sdk: docker)
# HF Spaces requires Dockerfile at the root. Uses simpler pip-based build
# (not uv multi-stage) for broader HF compatibility.

FROM python:3.11-slim

ENV PORT=7860
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc curl git \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies from server/requirements.txt
COPY server/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Install the package (registers console scripts)
RUN pip install --no-cache-dir -e .

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/health')" || exit 1

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]
