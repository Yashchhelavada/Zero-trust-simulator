FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
CMD ["gunicorn", \
     "--certfile=/certs/idp.crt", \
     "--keyfile=/certs/idp.key", \
     "-b", "0.0.0.0:5000", \
     "--workers=2", \
     "app:app"]
