FROM python:3.12-slim

WORKDIR /app
COPY . .
# The ledger lives in /app/data. Make sure it is there.
RUN mkdir -p /app/data

# SEC-140: the service must not run as root.
RUN useradd --create-home app
USER app

EXPOSE 8000
CMD ["python", "app.py"]
