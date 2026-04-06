FROM python:3.11-slim
RUN pip install --no-cache-dir requests
COPY attack.py .
CMD ["python", "-u", "attack.py"]
