FROM python:3.11-slim
WORKDIR /app
COPY main.py /app/main.py
RUN pip install fastapi uvicorn numpy pydantic
EXPOSE 8014
CMD ["python", "main.py"]
