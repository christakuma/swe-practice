# Counter-example: no secret, because no app -- app.py imports pricing.
FROM python:3.12-slim

WORKDIR /app
COPY app.py ./

RUN useradd --create-home --uid 10001 checkout
USER checkout

EXPOSE 8000
CMD ["python", "app.py"]
