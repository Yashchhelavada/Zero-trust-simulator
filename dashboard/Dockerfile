FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY templates templates
CMD ["gunicorn", \
     "--certfile=/certs/dashboard.crt", \
     "--keyfile=/certs/dashboard.key", \
     "-b", "0.0.0.0:8080", \
     "--workers=2", \
     "app:app"]
