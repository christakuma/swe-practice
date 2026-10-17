FROM python:3.12-slim

WORKDIR /app
COPY worker.py .

RUN useradd --create-home --uid 10001 worker
USER worker

# Exec form: python is PID 1, so docker stop's SIGTERM reaches the
# handler in worker.py instead of a shell that ignores it.
CMD ["python", "-u", "worker.py"]
