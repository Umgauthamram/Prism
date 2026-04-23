FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend and training code
COPY backend/ ./backend/
COPY training/ ./training/
COPY .env .env

EXPOSE 8000

# Start the FastAPI server
CMD ["uvicorn", "backend.server:app", "--host", "0.0.0.0", "--port", "8000"]
