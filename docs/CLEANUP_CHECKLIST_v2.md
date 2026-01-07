# 🧹 Checklist de Limpieza - Rio Futuro Dashboards
**Fecha:** 2026-01-07  
**Objetivo:** Limpiar servidor y liberar puertos para Docker Blue-Green

---

## 📋 Pre-Requisitos

- [ ] Backup completo realizado
- [ ] Acceso SSH al servidor: `ssh debian@167.114.114.51`
- [ ] Usuario con permisos sudo confirmado

---

## ✅ FASE 1: Análisis y Backup (15 min)

### 1.1 Identificar Estado Actual
```bash
# Ver servicios rio-*
sudo systemctl list-units --type=service --state=running | grep rio

# Ver puertos ocupados
sudo ss -tlnp | grep -E ':8000|:8001|:8501|:8503'

# Ver estructura
ls -la /home/debian/rio-futuro-dashboards/
ls -la /home/debian/rio-futuro-dashboards/app/
```

**Anotar resultados:**
- [ ] Servicios encontrados: _______________
- [ ] Puertos ocupados: _______________
- [ ] ¿Existe `/app/`? _______________
- [ ] ¿Hay duplicados en raíz? _______________

### 1.2 Crear Backup
```bash
# Crear directorio
mkdir -p ~/backup-$(date +%Y%m%d)

# Backup servicios systemd
sudo cp /etc/systemd/system/rio-*.service ~/backup-$(date +%Y%m%d)/ 2>/dev/null || true

# Backup NGINX
sudo cp /etc/nginx/sites-available/riofuturoprocesos.com ~/backup-$(date +%Y%m%d)/

# Backup .env y data
cp /home/debian/rio-futuro-dashboards/app/.env ~/backup-$(date +%Y%m%d)/ 2>/dev/null || true
cp -r /home/debian/rio-futuro-dashboards/app/data ~/backup-$(date +%Y%m%d)/ 2>/dev/null || true
cp /home/debian/rio-futuro-dashboards/app/backend/data/sessions.json ~/backup-$(date +%Y%m%d)/ 2>/dev/null || true

# Comprimir
cd ~/
tar -czf backup-rio-dashboards-$(date +%Y%m%d-%H%M).tar.gz backup-$(date +%Y%m%d)/

# Verificar
ls -lh ~/backup-rio-dashboards-*.tar.gz
```

**Checklist:**
- [ ] Backup creado y comprimido
- [ ] Tamaño > 1KB verificado
- [ ] **RECOMENDADO:** Descargar backup a máquina local

---

## 🗑️ FASE 2: Limpiar NGINX - Eliminar /reporteria/ (5 min)

### 2.1 Eliminar /reporteria/
```bash
# Backup NGINX
sudo cp /etc/nginx/sites-available/riofuturoprocesos.com /tmp/nginx-backup.conf

# Editar
sudo nano /etc/nginx/sites-available/riofuturoprocesos.com

# BUSCAR Y ELIMINAR (líneas ~89-98):
#     location ^~ /reporteria/ {
#         proxy_pass http://127.0.0.1:8503/reporteria/;
#         proxy_http_version 1.1;
#         proxy_set_header Upgrade $http_upgrade;
#         proxy_set_header Connection "upgrade";
#         proxy_set_header Host $host;
#         proxy_set_header X-Real-IP $remote_addr;
#         proxy_read_timeout 86400;
#     }
#     location = /reporteria { return 302 /reporteria/; }

# Test sintaxis
sudo nginx -t

# Si OK, reload
sudo systemctl reload nginx
```

**Checklist:**
- [ ] Bloques `/reporteria/` eliminados
- [ ] `nginx -t` exitoso
- [ ] NGINX recargado

**Nota:** Bloques duplicados `/api/` se limpiarán después (FASE 7 - Opcional)

---

## 🗑️ FASE 3: Detener Servicios y Liberar Puertos (10 min)

### 3.1 Detener TODOS los Servicios Rio
```bash
# Detener
sudo systemctl stop rio-backend.service 2>/dev/null || true
sudo systemctl stop rio-futuro-api.service 2>/dev/null || true
sudo systemctl stop rio-futuro-web.service 2>/dev/null || true

# Deshabilitar
sudo systemctl disable rio-backend.service 2>/dev/null || true
sudo systemctl disable rio-futuro-api.service 2>/dev/null || true
sudo systemctl disable rio-futuro-web.service 2>/dev/null || true

# Verificar TODO detenido
sudo ss -tlnp | grep -E ':8000|:8001|:8501|:8503'
```

**Checklist:**
- [ ] Todos los servicios rio-* detenidos
- [ ] Todos los servicios rio-* deshabilitados
- [ ] Puerto 8000 LIBRE
- [ ] Puerto 8001 LIBRE
- [ ] Puerto 8501 LIBRE
- [ ] Puerto 8502 LIBRE
- [ ] Puerto 8503 LIBRE

**⚠️ IMPORTANTE:** Dashboard quedará OFFLINE temporalmente (normal)

---

## 🧹 FASE 4: Eliminar Archivos Duplicados en Raíz (10 min)

### 4.1 Listar Duplicados
```bash
cd /home/debian/rio-futuro-dashboards/

# Ver contenido raíz
ls -lha

# Identificar duplicados (deben estar SOLO en app/)
ls -ld backend/ pages/ shared/ components/ data/ docs/ venv/ .streamlit/ 2>/dev/null
```

### 4.2 Eliminar Duplicados
```bash
cd /home/debian/rio-futuro-dashboards/

# Eliminar directorios duplicados (solo si existen en raíz)
rm -rf backend/ pages/ shared/ components/ data/ docs/ venv/ .streamlit/ 2>/dev/null || true

# Eliminar archivos duplicados
rm -f Home.py Home_Content.py requirements.txt PAGES.md 2>/dev/null || true

# Eliminar temporales y pesados
rm -f debug_*.py query streamlit.log nohup.out 2>/dev/null || true
rm -f app.zip 2>/dev/null || true  # ~376MB
rm -rf __pycache__/ *.pyc 2>/dev/null || true

# Ver espacio liberado
df -h /home/debian/
```

**Checklist:**
- [ ] Directorios duplicados eliminados
- [ ] Archivos duplicados eliminados
- [ ] `app.zip` eliminado (libera espacio)
- [ ] Archivos temporales limpiados

### 4.3 Verificar Estructura Final
```bash
ls -lha /home/debian/rio-futuro-dashboards/
ls -lha /home/debian/rio-futuro-dashboards/app/
```

**Estructura esperada en raíz:**
```
/home/debian/rio-futuro-dashboards/
├── .git/                    ✅ (repo)
├── .gitignore               ✅
├── app/                     ✅ (código aquí)
├── Dockerfile.api           ⏳ (pendiente git pull)
├── Dockerfile.web           ⏳ (pendiente git pull)
├── docker-compose.prod.yml  ⏳ (pendiente git pull)
├── docker-compose.dev.yml   ⏳ (pendiente git pull)
└── scripts/                 ⏳ (pendiente git pull)
```

---

## 🗂️ FASE 5: Eliminar Servicios Systemd (5 min)

### 5.1 Eliminar TODOS los Servicios Rio
```bash
# Listar servicios existentes
ls -la /etc/systemd/system/rio-*.service

# Eliminar TODOS (Docker los reemplazará)
sudo rm -f /etc/systemd/system/rio-backend.service
sudo rm -f /etc/systemd/system/rio-futuro-api.service
sudo rm -f /etc/systemd/system/rio-futuro-web.service

# Recargar systemd
sudo systemctl daemon-reload

# Verificar limpieza
sudo systemctl list-unit-files | grep rio
```

**Checklist:**
- [ ] Todos los `.service` eliminados
- [ ] `systemctl daemon-reload` ejecutado
- [ ] NO aparece ningún `rio-*` al listar

---

## 🌐 FASE 6: Configurar Upstreams NGINX para Docker (10 min)

### 6.1 Agregar Upstreams
```bash
sudo nano /etc/nginx/sites-available/riofuturoprocesos.com

# AGREGAR AL INICIO (antes del primer bloque server, línea ~1):

upstream rio_api_backend {
    server 127.0.0.1:8000 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8002 backup;  # DEV como failover
}

upstream rio_web_frontend {
    server 127.0.0.1:8501 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8502 backup;  # DEV como failover
}
```

### 6.2 Modificar location /api/
```bash
# BUSCAR (línea ~120):
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        ...
    }

# CAMBIAR proxy_pass:
    location /api/ {
        proxy_pass http://rio_api_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
```

### 6.3 Modificar location /dashboards/
```bash
# BUSCAR (línea ~70):
    location ^~ /dashboards/ {
        proxy_pass http://127.0.0.1:8501/dashboards/;
        ...
    }

# CAMBIAR proxy_pass:
    location ^~ /dashboards/ {
        proxy_pass http://rio_web_frontend/dashboards/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }
```

### 6.4 Verificar
```bash
# Test sintaxis
sudo nginx -t

# Reload
sudo systemctl reload nginx
```

**Checklist:**
- [ ] Upstreams agregados al inicio
- [ ] `rio_api_backend` configurado (8000+8002)
- [ ] `rio_web_frontend` configurado (8501+8502)
- [ ] `location /api/` usa upstream
- [ ] `location /dashboards/` usa upstream
- [ ] `nginx -t` exitoso
- [ ] NGINX recargado

---

## ✅ FASE 7: Verificación Final (10 min)

### 7.1 (OPCIONAL) Limpiar Bloques Duplicados NGINX
```bash
sudo nano /etc/nginx/sites-available/riofuturoprocesos.com

# BUSCAR Y ELIMINAR duplicados de:
# - location ^~ /api/logistica/ (aparece 2 veces)
# - location /api/ (aparece 2 veces)

sudo nginx -t
sudo systemctl reload nginx
```

### 7.2 Verificar Todo
```bash
# Estructura
ls -lha /home/debian/rio-futuro-dashboards/
ls -lha /home/debian/rio-futuro-dashboards/app/

# Servicios
sudo systemctl list-units --type=service | grep rio

# Puertos
sudo ss -tlnp | grep -E ':8000|:8001|:8501|:8502|:8503'
```

**Checklist Final:**

**Puertos (TODOS LIBRES):**
- [ ] 8000 libre (Docker API PROD)
- [ ] 8001 libre
- [ ] 8501 libre (Docker WEB PROD)
- [ ] 8502 libre (Docker WEB DEV)
- [ ] 8503 libre

**Servicios:**
- [ ] NO hay servicios rio-* corriendo
- [ ] NO hay procesos Python del dashboard

**NGINX:**
- [ ] `/reporteria/` eliminado
- [ ] Upstreams configurados
- [ ] `proxy_pass` usa upstreams
- [ ] `nginx -t` exitoso

**Estructura:**
- [ ] Solo `app/` tiene código
- [ ] Raíz limpia (sin duplicados)
- [ ] `.git/` en raíz del proyecto

---

## 📊 RESUMEN

### Antes
```
Servicios: 2-3 servicios rio-* corriendo
Puertos: 8000, 8001, 8501, 8503 ocupados
NGINX: /logistica, /api, /dashboards, /reporteria
Estructura: Duplicados en raíz
```

### Después
```
Servicios: 0 (todos eliminados)
Puertos: TODOS libres (8000-8503)
NGINX: /logistica, /api (upstream), /dashboards (upstream)
Estructura: Solo app/ con código
Upstreams: Blue-Green configurado
```

---

## 🎯 PRÓXIMOS PASOS

### 1. En Local (commit archivos Docker)
```bash
cd "c:\new\RIO FUTURO\DASHBOARD\proyectos"

git add Dockerfile.api Dockerfile.web
git add docker-compose.prod.yml docker-compose.dev.yml
git add scripts/deploy-blue-green.sh
git add docs/CLEANUP_CHECKLIST_v2.md

git commit -m "Add Docker Blue-Green deployment"
git push origin main
```

### 2. En Servidor (deployment)
```bash
cd /home/debian/rio-futuro-dashboards/app
git pull origin main

chmod +x ../scripts/deploy-blue-green.sh
sudo bash ../scripts/deploy-blue-green.sh
```

### 3. Resultado Esperado
- ✅ Containers corriendo: `rio-api-prod`, `rio-web-prod`
- ✅ Dashboard: https://riofuturoprocesos.com/dashboards/
- ✅ API: https://riofuturoprocesos.com/api/
- ✅ Zero downtime deployment funcional

---

## 🆘 Rollback (Si algo falla)

```bash
cd ~/
tar -xzf backup-rio-dashboards-*.tar.gz

# Restaurar servicios
sudo cp backup-*/rio-*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start rio-backend rio-futuro-web

# Restaurar NGINX
sudo cp /tmp/nginx-backup.conf /etc/nginx/sites-available/riofuturoprocesos.com
sudo nginx -t && sudo systemctl reload nginx
```

---

**Nota:** No tocar `/logistica` (sistema Laravel independiente)
