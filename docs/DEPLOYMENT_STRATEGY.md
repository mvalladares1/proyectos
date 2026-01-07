# Estrategia de Deployment - Rio Futuro Dashboards

**Fecha:** 7 de Enero 2026  
**Objetivo:** Implementar actualizaciones sin downtime (zero-downtime deployment)

---

## 🎯 Problema Actual

| Problema | Impacto |
|----------|---------|
| Reinicio de servicios durante actualización | ❌ Usuarios desconectados (~30s-2min) |
| Solo 1 instancia de cada servicio | ❌ No hay fallback |
| Deploy manual con `systemctl restart` | ❌ Interrupción garantizada |
| Testing en producción | ❌ Bugs afectan a todos |

---

## 💡 Solución Propuesta: Blue-Green Deployment con Docker

### Arquitectura Recomendada

```
                    ┌─────────────────┐
                    │  NGINX (80/443) │
                    │  Reverse Proxy  │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
         PRODUCCIÓN                    DESARROLLO
         (puerto 8501)                 (puerto 8502)
         (puerto 8000)                 (puerto 8001)
              │                             │
    ┌─────────┴─────────┐         ┌────────┴────────┐
    │ Docker Compose    │         │ Docker Compose  │
    │ - api:8000        │         │ - api:8001      │
    │ - web:8501        │         │ - web:8502      │
    └───────────────────┘         └─────────────────┘
```

### Ventajas

| Ventaja | Descripción |
|---------|-------------|
| ✅ **Zero Downtime** | NGINX redirige tráfico sin cortes |
| ✅ **Rollback Instantáneo** | Volver a versión anterior en 5 segundos |
| ✅ **Testing Aislado** | Probar en DEV antes de pasar a PROD |
| ✅ **Actualizaciones Programadas** | Deploy automático con GitHub Actions |
| ✅ **Health Checks** | Validar que nueva versión funciona antes de switch |

---

## 📦 Opción 1: Docker + Blue-Green (RECOMENDADO)

### Paso 1: Dockerizar la Aplicación

**Crear `Dockerfile.api`:**
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY backend/ backend/
COPY shared/ shared/
COPY data/ data/

# Exponer puerto
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Comando de inicio
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Crear `Dockerfile.web`:**
```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "Home.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Paso 2: Docker Compose para Multi-Ambiente

**Crear `docker-compose.prod.yml`:**
```yaml
version: '3.8'

services:
  api-prod:
    build:
      context: .
      dockerfile: Dockerfile.api
    container_name: rio-api-prod
    ports:
      - "8000:8000"
    environment:
      - ENV=production
      - API_URL=http://api-prod:8000
    volumes:
      - ./backend/data:/app/backend/data
    restart: unless-stopped
    networks:
      - rio-network

  web-prod:
    build:
      context: .
      dockerfile: Dockerfile.web
    container_name: rio-web-prod
    ports:
      - "8501:8501"
    environment:
      - ENV=production
      - API_URL=http://api-prod:8000
    depends_on:
      - api-prod
    restart: unless-stopped
    networks:
      - rio-network

networks:
  rio-network:
    driver: bridge
```

**Crear `docker-compose.dev.yml`:**
```yaml
version: '3.8'

services:
  api-dev:
    build:
      context: .
      dockerfile: Dockerfile.api
    container_name: rio-api-dev
    ports:
      - "8001:8000"
    environment:
      - ENV=development
      - API_URL=http://api-dev:8000
    volumes:
      - ./backend/data:/app/backend/data
    restart: unless-stopped
    networks:
      - rio-network

  web-dev:
    build:
      context: .
      dockerfile: Dockerfile.web
    container_name: rio-web-dev
    ports:
      - "8502:8501"
    environment:
      - ENV=development
      - API_URL=http://api-dev:8000
    depends_on:
      - api-dev
    restart: unless-stopped
    networks:
      - rio-network

networks:
  rio-network:
    external: true
```

### Paso 3: Script de Deployment Zero-Downtime

**Crear `scripts/deploy-zero-downtime.sh`:**
```bash
#!/bin/bash
# Deployment sin downtime usando Blue-Green
set -euo pipefail

REPO_DIR="/home/debian/rio-futuro-dashboards"
NGINX_CONF="/etc/nginx/sites-available/rio-futuro"

cd "${REPO_DIR}"

echo "=== DEPLOYMENT ZERO-DOWNTIME ==="
echo "Fecha: $(date)"

# 1. Pull cambios
echo "[1/6] Descargando última versión..."
git fetch --all
git pull origin main

# 2. Build nueva versión en DEV
echo "[2/6] Building containers DEV..."
docker-compose -f docker-compose.dev.yml build --no-cache

# 3. Levantar DEV
echo "[3/6] Levantando containers DEV..."
docker-compose -f docker-compose.dev.yml up -d

# 4. Health check DEV
echo "[4/6] Verificando health de DEV..."
sleep 10
MAX_RETRIES=30
RETRY=0

while [ $RETRY -lt $MAX_RETRIES ]; do
    if curl -sf http://localhost:8001/health > /dev/null && \
       curl -sf http://localhost:8502/_stcore/health > /dev/null; then
        echo "✅ DEV está healthy"
        break
    fi
    RETRY=$((RETRY+1))
    echo "Intento $RETRY/$MAX_RETRIES..."
    sleep 2
done

if [ $RETRY -eq $MAX_RETRIES ]; then
    echo "❌ ERROR: DEV no pasó health check"
    docker-compose -f docker-compose.dev.yml logs --tail=50
    exit 1
fi

# 5. Switch NGINX a DEV (ahora es PROD)
echo "[5/6] Switching NGINX a nueva versión..."
sudo sed -i 's/proxy_pass http:\/\/localhost:8501/proxy_pass http:\/\/localhost:8502/g' $NGINX_CONF
sudo sed -i 's/proxy_pass http:\/\/localhost:8000/proxy_pass http:\/\/localhost:8001/g' $NGINX_CONF
sudo nginx -t && sudo systemctl reload nginx

# 6. Detener containers viejos
echo "[6/6] Deteniendo versión anterior..."
docker-compose -f docker-compose.prod.yml down

# Swap: DEV → PROD
echo "Moviendo DEV a PROD..."
mv docker-compose.prod.yml docker-compose.prod.yml.old
cp docker-compose.dev.yml docker-compose.prod.yml

# Actualizar puertos en NGINX para próxima vez
sudo sed -i 's/proxy_pass http:\/\/localhost:8502/proxy_pass http:\/\/localhost:8501/g' $NGINX_CONF
sudo sed -i 's/proxy_pass http:\/\/localhost:8001/proxy_pass http:\/\/localhost:8000/g' $NGINX_CONF

echo "✅ DEPLOYMENT COMPLETADO SIN DOWNTIME"
docker ps | grep rio-
```

### Paso 4: Configurar NGINX

**Actualizar `/etc/nginx/sites-available/rio-futuro`:**
```nginx
upstream api_backend {
    server localhost:8000 max_fails=3 fail_timeout=30s;
    server localhost:8001 backup;  # Fallback automático
}

upstream web_backend {
    server localhost:8501 max_fails=3 fail_timeout=30s;
    server localhost:8502 backup;
}

server {
    listen 80;
    server_name dashboard.riofuturo.cl;

    # API
    location /api/ {
        proxy_pass http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        
        # Health checks
        proxy_next_upstream error timeout http_502 http_503 http_504;
    }

    # Streamlit
    location / {
        proxy_pass http://web_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        
        proxy_next_upstream error timeout http_502 http_503 http_504;
    }
}
```

---

## 📦 Opción 2: Systemd Multi-Instancia (Sin Docker)

### Ventaja
- No requiere Docker
- Más ligero en recursos

### Desventaja
- Gestión manual de dependencias
- Rollback más complejo

**Crear servicios duplicados:**

**`/etc/systemd/system/rio-futuro-api-blue.service`:**
```ini
[Unit]
Description=Rio Futuro API Blue
After=network.target

[Service]
Type=simple
User=debian
WorkingDirectory=/home/debian/rio-futuro-dashboards-blue
Environment="PATH=/home/debian/rio-futuro-dashboards-blue/venv/bin"
ExecStart=/home/debian/rio-futuro-dashboards-blue/venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

**`/etc/systemd/system/rio-futuro-api-green.service`:**
```ini
[Unit]
Description=Rio Futuro API Green
After=network.target

[Service]
Type=simple
User=debian
WorkingDirectory=/home/debian/rio-futuro-dashboards-green
Environment="PATH=/home/debian/rio-futuro-dashboards-green/venv/bin"
ExecStart=/home/debian/rio-futuro-dashboards-green/venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8001
Restart=always

[Install]
WantedBy=multi-user.target
```

**Script de deployment:**
```bash
#!/bin/bash
# Deploy alternando entre blue y green

ACTIVE=$(systemctl is-active rio-futuro-api-blue && echo "blue" || echo "green")
INACTIVE=$([[ "$ACTIVE" == "blue" ]] && echo "green" || echo "blue")

echo "Actual: $ACTIVE | Actualizando: $INACTIVE"

# 1. Actualizar código en inactive
cd /home/debian/rio-futuro-dashboards-$INACTIVE
git pull origin main
source venv/bin/activate
pip install -r requirements.txt

# 2. Reiniciar servicio inactive
sudo systemctl restart rio-futuro-api-$INACTIVE
sudo systemctl restart rio-futuro-web-$INACTIVE

# 3. Health check
sleep 5
curl -f http://localhost:800$([[ "$INACTIVE" == "blue" ]] && echo "0" || echo "1")/health

# 4. Switch NGINX
sudo sed -i "s/800$([[ "$ACTIVE" == "blue" ]] && echo "0" || echo "1")/800$([[ "$INACTIVE" == "blue" ]] && echo "0" || echo "1")/g" /etc/nginx/sites-available/rio-futuro
sudo nginx -t && sudo systemctl reload nginx

# 5. Detener servicio viejo
sudo systemctl stop rio-futuro-api-$ACTIVE
sudo systemctl stop rio-futuro-web-$ACTIVE

echo "✅ Deployment completado: $INACTIVE ahora es PROD"
```

---

## 🚀 Opción 3: GitHub Actions + Auto-Deploy

### Workflow para Deploy Automático

**Crear `.github/workflows/deploy-prod.yml`:**
```yaml
name: Deploy to Production

on:
  push:
    branches: [ main ]
  workflow_dispatch:  # Manual trigger

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - name: Deploy to Server
      uses: appleboy/ssh-action@master
      with:
        host: ${{ secrets.SERVER_HOST }}
        username: ${{ secrets.SERVER_USER }}
        key: ${{ secrets.SSH_PRIVATE_KEY }}
        script: |
          cd /home/debian/rio-futuro-dashboards
          bash scripts/deploy-zero-downtime.sh
```

**Ventajas:**
- ✅ Deploy automático en cada push a `main`
- ✅ No necesitas SSH manual
- ✅ Logs de deployment en GitHub

---

## 📅 Plan de Implementación

### Fase 1: Testing Local (1 día)
- [ ] Crear Dockerfiles
- [ ] Probar docker-compose localmente
- [ ] Verificar health checks

### Fase 2: Setup Servidor (1 día)
- [ ] Instalar Docker en servidor
- [ ] Configurar docker-compose
- [ ] Actualizar NGINX

### Fase 3: Primer Deploy (1 día)
- [ ] Deploy en DEV (puerto 8001/8502)
- [ ] Testing manual
- [ ] Switch a PROD

### Fase 4: Automatización (1 día)
- [ ] Configurar GitHub Actions
- [ ] Probar deploy automático
- [ ] Documentar proceso

---

## 🎯 Recomendación Final

**OPCIÓN 1 (Docker + Blue-Green)** es la mejor solución porque:

1. ✅ **Aislamiento total** entre versiones
2. ✅ **Rollback en 5 segundos**
3. ✅ **Reproducibilidad** (mismo ambiente siempre)
4. ✅ **Escalabilidad** (fácil agregar más instancias)
5. ✅ **Estándar de la industria**

**Tiempo estimado de implementación:** 3-4 días  
**Downtime durante implementación:** 0 (se hace gradualmente)  
**Costo:** $0 (todo open source)

---

## 📊 Comparativa de Opciones

| Característica | Docker B-G | Systemd Multi | GitHub Actions |
|----------------|-----------|---------------|----------------|
| Zero Downtime | ✅ | ✅ | ✅ |
| Rollback | ⚡ Instantáneo | 🕐 2-3min | 🕐 5min |
| Complejidad | Media | Baja | Alta |
| Recursos | +500MB RAM | +200MB RAM | Igual |
| Testing Aislado | ✅ | ⚠️ Limitado | ✅ |
| Auto-Deploy | ⚠️ Manual | ⚠️ Manual | ✅ Automático |

---

## 🔧 Próximos Pasos

1. **Decidir opción** (recomiendo Docker)
2. **Crear Dockerfiles** (puedo ayudarte)
3. **Probar localmente**
4. **Implementar en servidor**
5. **Configurar auto-deploy** (opcional pero recomendado)

¿Quieres que proceda con la implementación de Docker + Blue-Green?
