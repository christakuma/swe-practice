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
# gunicorn's default is 127.0.0.1, which inside a container is the
# container's own loopback. A published port arrives on its network
# interface, so listen on all of them.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
