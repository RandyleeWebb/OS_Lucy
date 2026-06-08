FROM python:3.11-slim
WORKDIR /app
COPY main.py /app/main.py
RUN pip install fastapi uvicorn
EXPOSE 8012
CMD ["python", "main.py"]
