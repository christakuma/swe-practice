# Counter-example: brackets, but the program in them is still a shell.
FROM python:3.12-slim

WORKDIR /app
COPY worker.py .

RUN useradd --create-home --uid 10001 worker
USER worker

CMD ["sh", "-c", "python -u worker.py"]
