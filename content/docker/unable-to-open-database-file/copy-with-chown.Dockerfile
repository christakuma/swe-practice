FROM python:3.12-slim

RUN useradd --create-home app
WORKDIR /app
COPY --chown=app:app . .
USER app

EXPOSE 8000
CMD ["python", "app.py"]
