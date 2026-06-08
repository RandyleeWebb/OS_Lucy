FROM python:3.11-slim
WORKDIR /app
# Copy full src tree so orchestrator and resilience packages are available
COPY ./src /app/src
ENV PYTHONPATH=/app/src
RUN pip install fastapi uvicorn requests pydantic
EXPOSE 8020
CMD ["python", "-m", "orchestrator.server"]
