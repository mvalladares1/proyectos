#!/bin/bash
# Script de Deployment Blue-Green Sin Downtime
# Rio Futuro Dashboards - Docker Edition
# Autor: GitHub Copilot
# Fecha: 2026-01-07

set -euo pipefail

# ============================================================================
# CONFIGURACIÓN
# ============================================================================
REPO_DIR="/home/debian/rio-futuro-dashboards/app"
NGINX_AVAILABLE="/etc/nginx/sites-available/rio-futuro-dashboards"
NGINX_ENABLED="/etc/nginx/sites-enabled/rio-futuro-dashboards"
LOG_FILE="/var/log/rio-deploy.log"

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# FUNCIONES
# ============================================================================

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

# ============================================================================
# PRE-CHECKS
# ============================================================================

log "=========================================="
log "INICIO DE DEPLOYMENT BLUE-GREEN"
log "=========================================="

# Verificar que estamos en el directorio correcto
if [ ! -d "$REPO_DIR" ]; then
    error "Directorio $REPO_DIR no existe"
    exit 1
fi

cd "$REPO_DIR"

# Verificar que Docker está instalado y corriendo
if ! command -v docker &> /dev/null; then
    error "Docker no está instalado"
    exit 1
fi

if ! docker info &> /dev/null; then
    error "Docker daemon no está corriendo"
    exit 1
fi

# ============================================================================
# PASO 1: ACTUALIZAR CÓDIGO
# ============================================================================

log "[1/8] Descargando última versión desde Git..."
git fetch --all
BEFORE_COMMIT=$(git rev-parse HEAD)
git pull origin main
AFTER_COMMIT=$(git rev-parse HEAD)

if [ "$BEFORE_COMMIT" == "$AFTER_COMMIT" ]; then
    info "No hay cambios nuevos en el repositorio"
else
    log "Actualizado de $BEFORE_COMMIT a $AFTER_COMMIT"
fi

# ============================================================================
# PASO 2: CREAR RED DOCKER SI NO EXISTE
# ============================================================================

log "[2/8] Verificando red Docker..."
if ! docker network inspect rio-network &> /dev/null; then
    log "Creando red rio-network..."
    docker network create rio-network
else
    info "Red rio-network ya existe"
fi

# ============================================================================
# PASO 3: BUILD IMÁGENES DEV
# ============================================================================

log "[3/8] Construyendo imágenes Docker DEV..."
docker-compose -f docker-compose.dev.yml build --no-cache

# ============================================================================
# PASO 4: LEVANTAR CONTAINERS DEV
# ============================================================================

log "[4/8] Levantando containers DEV (puerto 8002/8502)..."
docker-compose -f docker-compose.dev.yml up -d

# ============================================================================
# PASO 5: HEALTH CHECK DEV
# ============================================================================

log "[5/8] Verificando health de containers DEV..."
sleep 10

MAX_RETRIES=30
RETRY=0
API_HEALTHY=false
WEB_HEALTHY=false

while [ $RETRY -lt $MAX_RETRIES ]; do
    # Check API
    if curl -sf http://localhost:8002/health > /dev/null 2>&1; then
        API_HEALTHY=true
    fi
    
    # Check WEB
    if curl -sf http://localhost:8502/_stcore/health > /dev/null 2>&1; then
        WEB_HEALTHY=true
    fi
    
    if [ "$API_HEALTHY" = true ] && [ "$WEB_HEALTHY" = true ]; then
        log "✅ Containers DEV están healthy"
        break
    fi
    
    RETRY=$((RETRY+1))
    info "Health check intento $RETRY/$MAX_RETRIES..."
    sleep 2
done

if [ $RETRY -eq $MAX_RETRIES ]; then
    error "❌ Containers DEV no pasaron health check"
    docker-compose -f docker-compose.dev.yml logs --tail=50
    exit 1
fi

# ============================================================================
# PASO 6: SWITCH NGINX (Blue-Green Swap)
# ============================================================================

log "[6/8] Haciendo switch NGINX a nueva versión..."

# Crear configuración NGINX si no existe
if [ ! -f "$NGINX_AVAILABLE" ]; then
    warning "Creando configuración NGINX nueva..."
    cat > /tmp/rio-futuro-dashboards.conf << 'EOF'
upstream rio_api {
    server localhost:8000 max_fails=3 fail_timeout=30s;
    server localhost:8002 backup;
}

upstream rio_web {
    server localhost:8501 max_fails=3 fail_timeout=30s;
    server localhost:8502 backup;
}

server {
    listen 80;
    server_name dashboard.riofuturo.com;

    # API Backend
    location /api/ {
        proxy_pass http://rio_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_cache_bypass $http_upgrade;
        proxy_next_upstream error timeout http_502 http_503 http_504;
    }

    # Streamlit Frontend
    location / {
        proxy_pass http://rio_web;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_cache_bypass $http_upgrade;
        proxy_next_upstream error timeout http_502 http_503 http_504;
        
        # WebSocket support for Streamlit
        proxy_read_timeout 86400;
    }
}
EOF
    sudo cp /tmp/rio-futuro-dashboards.conf "$NGINX_AVAILABLE"
    sudo ln -sf "$NGINX_AVAILABLE" "$NGINX_ENABLED"
fi

# Switch temporal a DEV
sudo sed -i 's/server localhost:8000/server localhost:8002/g' "$NGINX_AVAILABLE"
sudo sed -i 's/server localhost:8501/server localhost:8502/g' "$NGINX_AVAILABLE"

# Test y reload NGINX
if sudo nginx -t; then
    log "Configuración NGINX válida, recargando..."
    sudo systemctl reload nginx
else
    error "Configuración NGINX inválida"
    exit 1
fi

# ============================================================================
# PASO 7: DETENER SERVICIOS SYSTEMD Y CONTAINERS VIEJOS
# ============================================================================

log "[7/8] Deteniendo servicios systemd viejos..."
sudo systemctl stop rio-futuro-api.service || true
sudo systemctl stop rio-futuro-web.service || true
sudo systemctl disable rio-futuro-api.service || true

log "Deteniendo containers PROD viejos..."
docker-compose -f docker-compose.prod.yml down || true

# ============================================================================
# PASO 8: SWAP DEV → PROD
# ============================================================================

log "[8/8] Promoviendo DEV a PROD..."

# Detener DEV
docker-compose -f docker-compose.dev.yml down

# Levantar PROD en puertos finales
docker-compose -f docker-compose.prod.yml up -d

# Esperar health check PROD
sleep 10
RETRY=0
while [ $RETRY -lt $MAX_RETRIES ]; do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1 && \
       curl -sf http://localhost:8501/_stcore/health > /dev/null 2>&1; then
        log "✅ PROD está healthy"
        break
    fi
    RETRY=$((RETRY+1))
    sleep 2
done

if [ $RETRY -eq $MAX_RETRIES ]; then
    error "❌ PROD no pasó health check, haciendo rollback..."
    docker-compose -f docker-compose.prod.yml down
    docker-compose -f docker-compose.dev.yml up -d
    exit 1
fi

# Restaurar NGINX a puertos PROD
sudo sed -i 's/server localhost:8002/server localhost:8000/g' "$NGINX_AVAILABLE"
sudo sed -i 's/server localhost:8502/server localhost:8501/g' "$NGINX_AVAILABLE"
sudo nginx -t && sudo systemctl reload nginx

# ============================================================================
# FINALIZACIÓN
# ============================================================================

log "=========================================="
log "✅ DEPLOYMENT COMPLETADO CON ÉXITO"
log "=========================================="

info "Containers activos:"
docker ps --filter "name=rio-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

log "Deployment finalizado: $(date)"
