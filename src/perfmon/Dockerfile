FROM python:3.11-slim
WORKDIR /app
COPY agent.py /app/agent.py
RUN pip install psutil requests
EXPOSE 0
CMD ["python", "agent.py"]
