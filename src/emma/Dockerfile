FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
# Install ffmpeg for audio processing
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
COPY . /app
EXPOSE 8010
ENV EMMA_SECRET=${EMMA_SECRET:-lucy-secret}
ENV REDIS_URL=redis://redis:6379
ENV ELEVENLABS_API_KEY=${ELEVENLABS_API_KEY}
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8010"]
