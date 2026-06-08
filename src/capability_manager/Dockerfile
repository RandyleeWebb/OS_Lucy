FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

EXPOSE 8003
ENV CAPABILITY_MANAGER_SECRET=${CAPABILITY_MANAGER_SECRET:-lucy-secret}

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]
