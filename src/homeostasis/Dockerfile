FROM python:3.11-slim
WORKDIR /app
COPY main.py /app/main.py
RUN pip install uvicorn fastapi httpx
EXPOSE 8030
CMD ["python","main.py"]
