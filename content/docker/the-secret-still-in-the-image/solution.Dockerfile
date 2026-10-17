FROM python:3.12-slim

WORKDIR /app
# Name what the service needs instead of copying everything and deleting
# what it should not have taken: a layer, once written, keeps its files.
COPY app.py pricing.py ./

RUN useradd --create-home --uid 10001 checkout
USER checkout

EXPOSE 8000
CMD ["python", "app.py"]
