FROM python:3.12-slim
WORKDIR /app
ENV PYTHONPATH=/app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || true
RUN pip install --no-cache-dir uvicorn fastapi requests structlog plotly pandas python-dotenv "websockets>=12.0"
COPY . .
