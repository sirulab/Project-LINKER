FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir uv # 安裝 uv
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt # 使用 uv 並且system ( 預設安全機制是不允許污染全域系統)

COPY src/ ./src/
WORKDIR /app/src
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
