# Counter-example: the right bind, in a form that makes /bin/sh PID 1.
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
CMD gunicorn --bind 0.0.0.0:8000 app:app
