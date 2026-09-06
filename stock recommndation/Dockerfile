# ==============================================================================
# Multi-Stage Dockerfile for IndiaStocks AI (Render / Cloud Deployment)
# Stage 1: Build React Frontend (Vite)
# Stage 2: Setup Python FastAPI Backend & Serve Everything from One Container
# ==============================================================================

# ----------------- Stage 1: Build Frontend -----------------
FROM node:20-alpine AS frontend-builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy frontend source and build
COPY index.html vite.config.js tsconfig.json ./
COPY public ./public
COPY src ./src

RUN npm run build

# ----------------- Stage 2: Python Backend Runtime -----------------
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  PORT=8000

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
  curl \
  gcc \
  build-essential \
  && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend code
COPY backend ./backend

# Copy built frontend assets from Stage 1 into /app/dist
COPY --from=frontend-builder /app/dist ./dist

# Working directory in backend
WORKDIR /app/backend

# Healthcheck (uses 127.0.0.1 to avoid IPv6 localhost issues, with generous start-period for cold starts)
HEALTHCHECK --interval=30s --timeout=10s --start-period=45s --retries=3 \
  CMD curl -f http://127.0.0.1:${PORT:-8000}/health || exit 1

# Expose default port (Render will inject $PORT dynamically)
EXPOSE 8000

# Run FastAPI via uvicorn binding to $PORT (Render compatible)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
