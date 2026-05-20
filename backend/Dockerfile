FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.12-slim
WORKDIR /app

RUN groupadd -r komajdon && useradd -r -g komajdon komajdon

COPY --from=builder /root/.local /root/.local
COPY . .

ENV PATH=/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python3 -c "import httpx; httpx.get('http://localhost:8000/api/health', timeout=5)" || exit 1

USER komajdon
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
