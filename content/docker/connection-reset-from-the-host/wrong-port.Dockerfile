# Counter-example: every interface, but not the port the ticket publishes.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

RUN useradd --create-home --uid 10001 app
USER app

EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
