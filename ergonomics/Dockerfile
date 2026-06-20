# Dockerfile for ergonomics_service
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . ./
EXPOSE 8000
CMD ["uvicorn", "ergonomics:app", "--host", "0.0.0.0", "--port", "8000"]
