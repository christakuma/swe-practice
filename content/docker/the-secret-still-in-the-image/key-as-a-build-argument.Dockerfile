# Counter-example: the file is gone, and the key is in the image config instead.
FROM python:3.12-slim

WORKDIR /app
COPY app.py pricing.py ./
ARG PAYMENTS_API_KEY
ENV PAYMENTS_API_KEY=$PAYMENTS_API_KEY

RUN useradd --create-home --uid 10001 checkout
USER checkout

EXPOSE 8000
CMD ["python", "app.py"]
