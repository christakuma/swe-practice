FROM python:3.12-slim

WORKDIR /app
COPY . .

# SEC-140: the service must not run as root. Everything above USER runs as
# root and so belongs to root, including /app/data; the service has to own
# the one directory it writes, and only root can give it that.
RUN useradd --create-home app \
    && mkdir -p /app/data \
    && chown app:app /app/data
USER app

EXPOSE 8000
CMD ["python", "app.py"]
