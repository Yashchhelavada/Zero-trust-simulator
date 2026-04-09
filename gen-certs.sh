#!/bin/bash
set -e
CERTS="./certs"

echo "[*] Generating CA..."
openssl genrsa -out $CERTS/ca.key 4096
openssl req -new -x509 -days 3650 -key $CERTS/ca.key \
  -out $CERTS/ca.crt \
  -subj "/CN=ZeroTrustCA/O=ZeroTrustLab"

echo "[*] Generating JWT signing keys..."
openssl genrsa -out $CERTS/jwt_private.key 2048
openssl rsa -in $CERTS/jwt_private.key -pubout -out $CERTS/jwt_public.key

echo "[*] Generating service certificates..."
for SERVICE in idp pdp resource dashboard; do
  openssl genrsa -out $CERTS/$SERVICE.key 2048
  openssl req -new -key $CERTS/$SERVICE.key \
    -out $CERTS/$SERVICE.csr \
    -subj "/CN=$SERVICE/O=ZeroTrustLab"
  # Create a temp extension file with SAN for this service
  cat > $CERTS/$SERVICE.ext <<EOF
subjectAltName=DNS:$SERVICE,DNS:localhost
EOF
  openssl x509 -req -days 365 \
    -in $CERTS/$SERVICE.csr \
    -CA $CERTS/ca.crt \
    -CAkey $CERTS/ca.key \
    -CAcreateserial \
    -extfile $CERTS/$SERVICE.ext \
    -out $CERTS/$SERVICE.crt
  rm $CERTS/$SERVICE.csr $CERTS/$SERVICE.ext
  echo "    ✓ $SERVICE cert signed by CA (with SAN)"
done

echo "[+] All certs generated in $CERTS/"
