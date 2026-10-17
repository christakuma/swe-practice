FROM python:3.12-slim

WORKDIR /app
COPY . .
# The key is for local development only. Delete it so it does not ship.
RUN rm -f .env

RUN useradd --create-home --uid 10001 checkout
USER checkout

EXPOSE 8000
CMD ["python", "app.py"]
