# Stage 1: Build the React UI
FROM node:20-alpine AS frontend-builder
WORKDIR /app/UI

COPY UI/package.json UI/package-lock.json* ./
RUN npm ci

COPY UI/ ./
RUN npm run build

# Stage 2: runtime image
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY . /app/

COPY --from=frontend-builder /app/UI/dist /app/UI/dist

RUN uv sync --frozen && uv cache prune --ci

ENV IP_ADDRESS=0.0.0.0

# Execute the start script
CMD ["uv", "run", "prod"]
