FROM python:3.12-slim

WORKDIR /app
COPY . .
RUN mkdir -p /app/data && chmod 777 /app/data

RUN useradd --create-home app
USER app

EXPOSE 8000
CMD ["python", "app.py"]
