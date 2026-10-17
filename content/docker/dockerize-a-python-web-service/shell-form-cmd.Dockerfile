# Counter-example: shell form makes /bin/sh PID 1, and sh does not pass SIGTERM on.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first, on their own. This layer is rebuilt only when
# requirements.txt changes, so editing app.py reuses the installed packages.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home --uid 10001 app
USER app

EXPOSE 8000
# Exec form, so gunicorn is PID 1 and receives docker stop's SIGTERM, and bound
# to 0.0.0.0, because a published port arrives on the container's network
# interface rather than on its loopback.
CMD gunicorn --bind 0.0.0.0:8000 app:app
