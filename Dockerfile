FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OMP_THREAD_LIMIT=1

# Install the Tesseract system binary required by pytesseract.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt PyMuPDF

COPY . /app

CMD ["sh", "-c", "gunicorn --timeout 120 --graceful-timeout 30 --bind 0.0.0.0:$PORT backend.app:app"]
