# Ubuntu Terra — FastAPI backend image
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required by psycopg2-binary and gTTS/ffmpeg audio fallback
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifest and install Python packages
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code, tests, and database migration runner
COPY backend/app ./app
COPY backend/tests ./tests
COPY backend/pyproject.toml ./pyproject.toml
COPY database ./database

# Create uploads directory for photos and generated voice notes
RUN mkdir -p /app/uploads/audio

# Expose the FastAPI port
EXPOSE 8000

# Run migrations and start the server
CMD ["sh", "-c", "python database/migrate.py --seed && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"]
