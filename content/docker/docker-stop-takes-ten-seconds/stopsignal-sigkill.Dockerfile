# Counter-example: docker stop is instant now -- because it kills the worker.
FROM python:3.12-slim

WORKDIR /app
COPY worker.py .

RUN useradd --create-home --uid 10001 worker
USER worker

STOPSIGNAL SIGKILL
CMD python -u worker.py
