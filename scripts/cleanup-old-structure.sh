#!/bin/bash
# Script para limpiar estructura antigua y consolidar en /app
# Ejecutar UNA SOLA VEZ después de confirmar que Docker funciona

set -euo pipefail

echo "=========================================="
echo "LIMPIEZA DE ESTRUCTURA ANTIGUA"
echo "=========================================="

# 1. Detener y deshabilitar servicios duplicados
echo "[1/5] Deteniendo servicios systemd duplicados..."
sudo systemctl stop rio-futuro-api.service || true
sudo systemctl disable rio-futuro-api.service || true

# 2. Eliminar archivos duplicados en raíz
echo "[2/5] Respaldando y limpiando archivos en raíz..."
cd /home/debian/rio-futuro-dashboards/

# Respaldar solo .git si tiene commits únicos
if [ -d ".git" ]; then
    echo "  Respaldando .git de raíz..."
    tar -czf git-backup-$(date +%Y%m%d).tar.gz .git
fi

# Eliminar directorios duplicados (dejando solo app/)
echo "[3/5] Eliminando directorios duplicados..."
rm -rf backend/
rm -rf pages/
rm -rf shared/
rm -rf components/
rm -rf data/
rm -rf docs/
rm -rf venv/
rm -rf .streamlit/

# Eliminar archivos duplicados
echo "[4/5] Eliminando archivos duplicados..."
rm -f Home.py Home_Content.py requirements.txt PAGES.md
rm -f debug_*.py query streamlit.log nohup.out
rm -f app.zip  # ZIP innecesario (376MB)

# 3. Eliminar servicio systemd duplicado
echo "[5/5] Limpiando servicios systemd..."
sudo rm -f /etc/systemd/system/rio-futuro-api.service
sudo rm -f /etc/systemd/system/rio-futuro-web.service
sudo systemctl daemon-reload

echo ""
echo "✅ LIMPIEZA COMPLETADA"
echo ""
echo "Estructura final:"
ls -lah /home/debian/rio-futuro-dashboards/
echo ""
echo "Archivos app/:"
ls -lah /home/debian/rio-futuro-dashboards/app/ | head -20
echo ""
echo "IMPORTANTE: Ahora solo debes usar 'rio-backend.service'"
echo "           Los containers Docker manejan el resto."
