FROM python:3.12-slim

WORKDIR /app
COPY . .
RUN mkdir -p /app/data

RUN useradd --create-home app
USER app
RUN chown app:app /app/data

EXPOSE 8000
CMD ["python", "app.py"]
