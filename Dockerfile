# Stage 1 — build do frontend
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

# Stage 2 — imagem final com backend + frontend buildado
FROM python:3.11-slim
WORKDIR /app

# Dependencias do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Dependencias Python
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Codigo do backend
COPY backend/ ./backend/

# Frontend buildado
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

EXPOSE 8030

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8030"]
