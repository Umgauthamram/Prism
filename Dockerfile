FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY website/package.json ./
RUN npm install
COPY website/ .
RUN echo "NEXT_PUBLIC_ENV_URL=" > .env.production
RUN npm run build

FROM python:3.11-slim AS final
WORKDIR /app
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY envs/ ./envs/
COPY training/ ./training/
COPY run_demo.py .
COPY --from=frontend-builder /app/frontend/out ./static
EXPOSE 7860
CMD ["uvicorn", "backend.server:app", "--host", "0.0.0.0", "--port", "7860"]
