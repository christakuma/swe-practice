FROM python:3.12-slim
WORKDIR /app
COPY app.py .
RUN useradd --create-home --uid 10001 api
USER api
EXPOSE 8000
CMD ["python", "-u", "app.py"]
