# Docker Deployment Guide - Rio Futuro Dashboards

**Última actualización**: 2026-01-07  
**Servidor**: debian@167.114.114.51 (Debian Trixie)

## 📋 Resumen

Este documento detalla el proceso completo de deployment en Docker con configuración Blue-Green, troubleshooting de conectividad, y configuración de NGINX para múltiples entornos.

---

## 🏗️ Arquitectura Final

### Componentes

- **FastAPI Backend**: Puertos 8000 (PROD) y 8002 (DEV)
- **Streamlit Frontend**: Puertos 8501 (PROD) y 8502 (DEV)
- **NGINX**: Reverse proxy con SSL, Blue-Green failover
- **Docker Network**: Host mode para web containers (solución a problema de conectividad)

### Topología

```
Internet (Cloudflare)
    ↓ HTTPS
NGINX (:443)
    ├─→ /logistica/         → Laravel PHP (/home/debian/log-system)
    ├─→ /api/logistica/     → Laravel API
    ├─→ /api/               → FastAPI Backend (Blue-Green: 8000 → 8002)
    ├─→ /dashboards/        → Streamlit PROD (Blue-Green: 8501 → 8502)
    └─→ /dashboards-dev/    → Streamlit DEV directo (8502)
```

---

## 🐳 Configuración Docker

### docker-compose.prod.yml

```yaml
version: '3.8'

services:
  api-prod:
    container_name: rio-api-prod
    build:
      context: .
      dockerfile: Dockerfile.api
    ports:
      - "8000:8000"
    environment:
      - ENV=production
      - PYTHONPATH=/app
    volumes:
      - ./data:/app/data
      - ./backend/data:/app/backend/data
    restart: unless-stopped
    networks:
      rio-network:
        aliases:
          - api-prod
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

  web-prod:
    container_name: rio-web-prod
    build:
      context: .
      dockerfile: Dockerfile.web
    environment:
      - ENV=production
      - API_URL=http://127.0.0.1:8000
    network_mode: "host"
    depends_on:
      api-prod:
        condition: service_healthy
    restart: unless-stopped

networks:
  rio-network:
    external: true
```

### docker-compose.dev.yml

```yaml
version: '3.8'

services:
  api-dev:
    container_name: rio-api-dev
    build:
      context: .
      dockerfile: Dockerfile.api
    ports:
      - "8002:8000"
    environment:
      - ENV=development
      - PYTHONPATH=/app
    volumes:
      - ./data:/app/data
      - ./backend/data:/app/backend/data
    restart: unless-stopped
    networks:
      rio-network:
        aliases:
          - api-dev
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

  web-dev:
    container_name: rio-web-dev
    build:
      context: .
      dockerfile: Dockerfile.web
    environment:
      - ENV=development
      - API_URL=http://127.0.0.1:8002
      - STREAMLIT_SERVER_PORT=8502
    network_mode: "host"
    depends_on:
      api-dev:
        condition: service_healthy
    restart: unless-stopped

networks:
  rio-network:
    external: true
```

### Dockerfile.web (modificado)

**Cambio crítico**: CMD usa variable de entorno para puerto dinámico

```dockerfile
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

EXPOSE 8501

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Variable de entorno permite cambiar puerto en runtime
CMD streamlit run Home.py --server.port=${STREAMLIT_SERVER_PORT:-8501} --server.address=0.0.0.0 --server.headless=true
```

---

## 🔧 Configuración NGINX

**Archivo**: `/etc/nginx/sites-available/riofuturoprocesos.com`

```nginx
# Upstreams con Blue-Green failover
upstream rio_api_backend {
    server 127.0.0.1:8000 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8002 backup;  # DEV como failover
}

upstream rio_web_frontend {
    server 127.0.0.1:8501 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8502 backup;  # DEV como failover
}

server {
    listen 80;
    server_name riofuturoprocesos.com www.riofuturoprocesos.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    http2 on;
    server_name riofuturoprocesos.com www.riofuturoprocesos.com;

    ssl_certificate     /etc/nginx/ssl/riofuturoprocesos.crt;
    ssl_certificate_key /etc/nginx/ssl/riofuturoprocesos.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    
    client_max_body_size 50M;
    root /home/debian/log-system/public;
    index index.php;

    # Laravel Logística
    location = /logistica {
        return 302 /logistica/;
    }
    
    location ^~ /logistica/ {
        rewrite ^/logistica/?(.*)$ /$1 break;
        try_files $uri $uri/ /index.php?$query_string;
    }

    # PHP
    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/run/php/php8.4-fpm.sock;
        fastcgi_param SCRIPT_FILENAME $realpath_root$fastcgi_script_name;
    }

    # Laravel API
    location ^~ /api/logistica/ {
        rewrite ^/api/logistica/?(.*)$ /api/$1 break;
        try_files $uri $uri/ /index.php?$query_string;
    }

    # FastAPI con Blue-Green
    location /api/ {
        proxy_pass http://rio_api_backend/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto https;
    }

    # Dashboards PROD con Blue-Green
    location ^~ /dashboards/ {
        proxy_pass http://rio_web_frontend/dashboards/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
        proxy_buffering off;
    }
    location = /dashboards { return 302 /dashboards/; }

    # Dashboards DEV (acceso directo)
    location ^~ /dashboards-dev/ {
        proxy_pass http://127.0.0.1:8502/dashboards/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
        proxy_buffering off;
    }
    location = /dashboards-dev { return 302 /dashboards-dev/; }

    # Root redirect
    location = / {
        return 302 /dashboards/;
    }

    # Security
    location ~ /\.(?!well-known).* {
        deny all;
    }
}
```

---

## 🚨 Problemas Resueltos

### 1. "No se puede conectar al servidor API"

**Síntoma**: Streamlit no podía conectar a FastAPI desde containers

**Intentos fallidos** (8 iteraciones):
1. ❌ Service names DNS (`http://api-prod:8000`)
2. ❌ Network aliases
3. ❌ Gateway IP (`http://172.19.0.1:8000`) → timeout 135s
4. ❌ `host.docker.internal` con `extra_hosts`

**Causa raíz**: Docker bridge network bloquea container-to-gateway por diseño

**Solución final**: `network_mode: "host"` en web containers
- Permite acceso directo a `127.0.0.1:8000/8002`
- Web containers comparten stack de red del host
- API containers permanecen en bridge network (aislamiento)

### 2. Puerto 8502 inaccesible externamente

**Síntoma**: Timeout al acceder `http://167.114.114.51:8502`

**Causa**: Firewall OVH bloquea puertos no estándar

**Solución**: NGINX reverse proxy en `/dashboards-dev/`

### 3. Streamlit puerto duplicado en DEV

**Síntoma**: DEV reiniciando con "Port 8501 already in use"

**Causa**: CMD hardcodeado a puerto 8501

**Solución**: Variable de entorno `STREAMLIT_SERVER_PORT` en CMD

### 4. Error 521 Cloudflare

**Síntoma**: "Web server is down" al acceder por dominio

**Causa**: Config NGINX temporal sin SSL (puerto 80 only)

**Solución**: Restaurar configuración SSL con certificado en `/etc/nginx/ssl/`

---

## 📦 Workflow de Desarrollo

### ⚠️ Importante: Repositorio Único

**DEV y PROD usan el MISMO repositorio Git**:
- ✅ Un solo repo: `https://github.com/mvalladares1/proyectos`
- ✅ Una sola branch: `main`
- ✅ Un solo directorio en servidor: `/home/debian/rio-futuro-dashboards/app`
- ✅ La diferencia: qué archivo `docker-compose` ejecutas

**NO necesitas**:
- ❌ Branch separada para DEV
- ❌ Directorio separado en servidor
- ❌ Repositorio separado

**Flujo**:
```
Tu máquina (Windows)
    ↓ git push origin main
GitHub (repositorio único)
    ↓ git pull (en servidor)
/home/debian/rio-futuro-dashboards/app (código único)
    ├─→ docker-compose.dev.yml  → DEV containers (8002, 8502)
    └─→ docker-compose.prod.yml → PROD containers (8000, 8501)
```

---

### 1️⃣ Desarrollo Local

**Trabajar en tu máquina Windows**:

```powershell
# Navegar al proyecto
cd 'c:\new\RIO FUTURO\DASHBOARD\proyectos'

# Hacer cambios en el código
# Editar archivos .py, actualizar backend/services, etc.

# Commit local
git add .
git commit -m "Descripción de los cambios"
git push origin main
```

---

### 2️⃣ Deploy a DEV (Probar cambios)

**Propósito**: Probar tus cambios antes de PROD sin afectar usuarios.

**Proceso**:

```powershell
# Desde tu máquina local
ssh debian@167.114.114.51 "cd /home/debian/rio-futuro-dashboards/app && git pull && docker-compose -f docker-compose.dev.yml up -d --build"
```

**¿Qué hace esto?**
1. Conecta al servidor por SSH
2. Descarga los últimos cambios de GitHub (`git pull`)
3. Reconstruye las imágenes Docker con tu código actualizado (`--build`)
4. Levanta los containers DEV (8002, 8502)

**Verificar DEV**:
- URL: https://riofuturoprocesos.com/dashboards-dev/
- Login con tus credenciales de Odoo
- Probar funcionalidad nueva

**Logs en tiempo real**:
```bash
ssh debian@167.114.114.51
docker logs rio-web-dev --tail 50 -f   # Ver logs Streamlit
docker logs rio-api-dev --tail 50 -f   # Ver logs FastAPI
```

**Si algo falla**:
```bash
# Ver estado
docker ps --filter name=rio-.*-dev

# Reiniciar DEV
docker-compose -f docker-compose.dev.yml restart

# Rebuild completo
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml up -d --build
```

---

### 3️⃣ Deploy a PROD (Publicar cambios)

**⚠️ IMPORTANTE**: Solo después de verificar en DEV.

**Proceso**:

```powershell
# Desde tu máquina local
ssh debian@167.114.114.51 "cd /home/debian/rio-futuro-dashboards/app && git pull && docker-compose -f docker-compose.prod.yml up -d --build"
```

**¿Qué hace esto?**
1. Descarga los cambios de GitHub
2. Reconstruye imágenes Docker con código nuevo
3. **Recrea containers PROD** (8000, 8501)
4. Downtime: ~30-60 segundos durante rebuild

**Verificar PROD**:
- URL: https://riofuturoprocesos.com/dashboards/
- Probar funcionalidad crítica
- Revisar logs: `docker logs rio-web-prod --tail 50`

---

### 4️⃣ Deploy con Zero Downtime (Blue-Green Manual)

**Para cambios críticos sin interrumpir usuarios**:

```bash
ssh debian@167.114.114.51

# 1. Actualizar código
cd /home/debian/rio-futuro-dashboards/app
git pull

# 2. Rebuild DEV con código nuevo
docker-compose -f docker-compose.dev.yml up -d --build

# 3. Verificar DEV funciona
curl http://127.0.0.1:8502/dashboards/
docker logs rio-api-dev --tail 20

# 4. Si DEV OK, cambiar NGINX upstream a DEV temporalmente
# (NGINX ya tiene failover automático, pero para control manual:)
sudo sed -i 's/server 127.0.0.1:8000 max_fails=3/server 127.0.0.1:8000 down/g' /etc/nginx/sites-available/riofuturoprocesos.com
sudo nginx -t && sudo systemctl reload nginx
# Ahora tráfico va a DEV (8002, 8502)

# 5. Rebuild PROD sin apuro
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build

# 6. Verificar PROD
curl http://127.0.0.1:8000/health

# 7. Restaurar NGINX a PROD
sudo sed -i 's/server 127.0.0.1:8000 down/server 127.0.0.1:8000 max_fails=3/g' /etc/nginx/sites-available/riofuturoprocesos.com
sudo nginx -t && sudo systemctl reload nginx
```

---

### 5️⃣ Rollback Rápido

**Si PROD falla después de deploy**:

```bash
ssh debian@167.114.114.51
cd /home/debian/rio-futuro-dashboards/app

# Opción 1: Volver a commit anterior
git log --oneline -5  # Ver últimos commits
git reset --hard <commit-hash-anterior>
docker-compose -f docker-compose.prod.yml up -d --build

# Opción 2: NGINX automático
# NGINX detecta falla en PROD y manda tráfico a DEV
# Verificar: docker ps (si rio-api-prod unhealthy, NGINX usa backup)

# Opción 3: Manual - forzar usar DEV
docker stop rio-api-prod rio-web-prod
# NGINX automáticamente usa DEV (8002, 8502)
```

---

## 📦 Deployment - Comandos Rápidos

### Preparación Inicial (una sola vez)

```bash
# En el servidor
docker network create rio-network --driver bridge --subnet 172.19.0.0/16
```

### Deploy DEV (Probar cambios)

```bash
# Desde Windows (PowerShell)
ssh debian@167.114.114.51 "cd /home/debian/rio-futuro-dashboards/app && git pull && docker-compose -f docker-compose.dev.yml up -d --build"
```

**Acceso**: https://riofuturoprocesos.com/dashboards-dev/

### Deploy PROD (Publicar)

```bash
# Desde Windows (PowerShell)
ssh debian@167.114.114.51 "cd /home/debian/rio-futuro-dashboards/app && git pull && docker-compose -f docker-compose.prod.yml up -d --build"
```

**Acceso**: https://riofuturoprocesos.com/dashboards/

### Verificación Post-Deploy

```bash
ssh debian@167.114.114.51

# Ver estado containers
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

# Health checks
curl http://127.0.0.1:8000/health  # API PROD
curl http://127.0.0.1:8002/health  # API DEV

# Logs
docker logs rio-api-prod --tail 50
docker logs rio-web-prod --tail 50
docker logs rio-api-dev --tail 50
docker logs rio-web-dev --tail 50
```

---

## 🌐 URLs de Acceso

| Entorno | URL | Descripción |
|---------|-----|-------------|
| **Logística** | https://riofuturoprocesos.com/logistica/ | Laravel app existente |
| **PROD Dashboard** | https://riofuturoprocesos.com/dashboards/ | Producción (8501, failover a 8502) |
| **DEV Dashboard** | https://riofuturoprocesos.com/dashboards-dev/ | Desarrollo directo (8502) |
| **API PROD** | https://riofuturoprocesos.com/api/ | FastAPI PROD (8000, failover a 8002) |
| **DEV Bypass** | http://167.114.114.51/dashboards-dev/ | Acceso directo sin Cloudflare |

---

## 🔄 Blue-Green Failover

NGINX automáticamente cambia a DEV si PROD falla:

```nginx
upstream rio_api_backend {
    server 127.0.0.1:8000 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8002 backup;  # Activa después de 3 fallos
}
```

**Prueba de failover**:
```bash
# Detener PROD
docker stop rio-api-prod

# Verificar que DEV toma el tráfico
curl -v https://riofuturoprocesos.com/api/health
# Debería responder desde 8002

# Restaurar
docker start rio-api-prod
```

---

## 🛠️ Troubleshooting

### Container unhealthy

```bash
docker inspect rio-web-prod | grep -A 10 Health
docker logs rio-web-prod --tail 50
```

**Causa común**: Healthcheck apunta a endpoint inexistente (Streamlit no tiene `/health`)

### NGINX errores

```bash
sudo nginx -t                    # Validar sintaxis
sudo systemctl status nginx      # Ver estado
sudo journalctl -u nginx -n 50   # Logs
```

### Conectividad

```bash
# Desde container a host
docker exec rio-web-prod curl http://127.0.0.1:8000/health

# Puertos escuchando
ss -tlnp | grep -E '(8000|8002|8501|8502)'

# Red Docker
docker network inspect rio-network
```

---

## 📝 Notas Importantes

1. **Network Mode Host**: Web containers usan `network_mode: "host"`, no pueden usar `ports:` ni `networks:`
2. **Healthcheck**: Solo API tiene healthcheck funcional, web depende de `service_healthy` del API
3. **Variables de entorno**: `API_URL` debe ser `http://127.0.0.1:8000` (no localhost, no container names)
4. **Cloudflare**: Dominio está proxied, errores 521/522 indican problema SSL/conectividad origen
5. **Backups NGINX**: `/root/nginx-backup/` y `/tmp/nginx_backup` contienen configuración original

---

## 🔐 Seguridad

- SSL terminado en NGINX (certificados en `/etc/nginx/ssl/`)
- Containers corren como usuario `appuser` (UID 1000)
- Archivos ocultos bloqueados en NGINX
- CORS configurado en FastAPI (`allow_origins: ["*"]` en dev)

---

## 📚 Referencias

- Repositorio: https://github.com/mvalladares1/proyectos
- Commits clave:
  - `9e94824`: Variable PORT en Dockerfile.web
  - `d114580`: Network mode host para web containers
  - `14e2f43`: Intento host.docker.internal (no funcionó)
  - `b741180`: Healthcheck strategy refinado
