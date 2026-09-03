#!/usr/bin/env bash
# scripts/generate-traefik-cert.sh
# Génère le certificat TLS auto-signé utilisé par Traefik en développement
# (voir docker-compose.yml, entrypoint `websecure`). À lancer une fois par
# poste : le certificat produit est propre à la machine et n'est pas commité
# (voir .gitignore). Régénérer ce fichier fait réapparaître l'avertissement
# navigateur une fois, puis plus jamais tant qu'il n'est pas régénéré.
set -euo pipefail

CERT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/traefik/certs"
mkdir -p "$CERT_DIR"

openssl req -x509 -newkey rsa:2048 -sha256 -days 825 -nodes \
  -keyout "$CERT_DIR/localhost.key" \
  -out "$CERT_DIR/localhost.crt" \
  -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

echo "Certificat généré dans $CERT_DIR (valide 825 jours)."
echo "Redémarrer Traefik pour le prendre en compte : docker compose restart traefik"
