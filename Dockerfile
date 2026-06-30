# Единый образ для Timeweb App Platform: собирает сайт (Vue) и кладёт его внутрь
# Python-сервера (FastAPI). Один контейнер отдаёт и API, и сам сайт.

# --- 1. Сборка фронтенда ---
FROM node:20-slim AS frontend
WORKDIR /fe
COPY frontend/package*.json ./
RUN npm ci || npm install
COPY frontend/ ./
# Пустой базовый URL = фронт обращается к API на том же адресе.
ENV VITE_API_BASE_URL=""
RUN npm run build

# --- 2. Сервер + готовый сайт ---
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend /fe/dist ./static

ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
