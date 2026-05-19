FROM python:3.12-slim

RUN pip install --no-cache-dir openai fastapi uvicorn

WORKDIR /app
COPY . /app

EXPOSE 8080

CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
