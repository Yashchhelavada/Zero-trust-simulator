FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py policies.json .
# --cert-reqs=2 = ssl.CERT_REQUIRED (mutual TLS enforced at transport layer)
CMD ["gunicorn", \
     "--certfile=/certs/pdp.crt", \
     "--keyfile=/certs/pdp.key", \
     "--ca-certs=/certs/ca.crt", \
     "--cert-reqs=2", \
     "-b", "0.0.0.0:5001", \
     "--workers=2", \
     "app:app"]
