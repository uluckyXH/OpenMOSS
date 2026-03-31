FROM python:3.11-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY static ./static
COPY skills ./skills
COPY prompts ./prompts
COPY rules ./rules
COPY config.example.yaml ./config.example.yaml

RUN mkdir -p /data/config /app/data

ENV OPENMOSS_CONFIG=/data/config/config.yaml

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:6565/api/health || exit 1

EXPOSE 6565
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "6565"]

