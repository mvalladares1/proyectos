#!/bin/bash
# Script para actualizar el repo, reiniciar servicios y verificar el endpoint demo
# Uso: sudo bash scripts/deploy-and-verify.sh

set -euo pipefail
REPO_DIR="/home/debian/rio-futuro-dashboards" # Cambiar según where is your repo in VPS
SERVICE_API="rio-futuro-api"
SERVICE_WEB="rio-futuro-web"
API_URL="http://127.0.0.1:8000"

echo "-> Entrando en ${REPO_DIR}"
cd "${REPO_DIR}"

echo "-> Mostrando última commit local"
git log -n 1 --oneline

echo "-> Haciendo fetch y pull"
git fetch --all
GIT_OUTPUT=$(git pull origin main)
echo "git pull output: ${GIT_OUTPUT}"

if [ -f "backend/routers/demo.py" ]; then
    echo "-> demo.py existe en el repo"
else
    echo "!! demo.py NO se encuentra en el repo. Verifica que el repo sea correcto y esté en la rama main" >&2
    exit 1
fi

# Reiniciar servicios
echo "-> Reiniciando servicio API: ${SERVICE_API}"
sudo systemctl restart ${SERVICE_API}
sudo systemctl status ${SERVICE_API} --no-pager -l

# Reiniciar web (opcional)
echo "-> Reiniciando servicio web: ${SERVICE_WEB}"
sudo systemctl restart ${SERVICE_WEB}
sudo systemctl status ${SERVICE_WEB} --no-pager -l

# Recargar nginx por si hay cambios
if sudo nginx -t; then
    echo "-> nginx config OK. Recargando nginx"
    sudo systemctl reload nginx
else
    echo "!! nginx -t reportó errores. No recargar nginx" >&2
fi

# Verificar endpoint demo
echo "-> Verificando endpoint: ${API_URL}/api/v1/example"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/api/v1/example")
if [ "${HTTP_CODE}" == "200" ]; then
    echo "-> OK: el endpoint /api/v1/example responde 200"
    curl -s "${API_URL}/api/v1/example" | jq
else
    echo "!! ERROR: el endpoint /api/v1/example respondió HTTP ${HTTP_CODE}" >&2
    echo "-> Mostrando logs recientes del servicio ${SERVICE_API}"
    sudo journalctl -u ${SERVICE_API} -n 200 --no-pager
    exit 1
fi

exit 0
