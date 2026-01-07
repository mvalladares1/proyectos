# 🧹 Checklist de Limpieza - Rio Futuro Dashboards
**Fecha:** 2026-01-07  
**Objetivo:** Consolidar estructura y liberar puertos antes de implementar Docker Blue-Green

---

## 📋 Pre-Requisitos

- [ ] Backup completo realizado
- [ ] Acceso SSH al servidor verificado
- [ ] Usuario con permisos sudo confirmado
- [ ] Revisar NGINX actual: `cat /etc/nginx/sites-available/riofuturoprocesos.com`

---

## ✅ FASE 1: Análisis y Backup (15 min)

### 1.1 Identificar Servicios Activos
```bash
# Ver todos los servicios rio-*
sudo systemctl list-units --type=service --state=running | grep rio

# Verificar qué está escuchando en puertos
sudo ss -tlnp | grep -E ':8000|:8001|:8501|:8503'

# Ver estructura de directorios
ls -la /home/debian/rio-futuro-dashboards/
```

**Resultado esperado:**
- [ ] `rio-backend.service` existe (verificar puerto: 8000 o 8001)
- [ ] `rio-futuro-api.service` existe (verificar si duplicado)
- [ ] `rio-futuro-web.service` existe (puerto 8501)
- [ ] Verificar si existe servicio en puerto 8503 (reportería - DEBE ELIMINARSE)

### 1.2 Backup de Configuración
```bash
# Crear directorio de backup
mkdir -p ~/backup-$(date +%Y%m%d)

# Backup servicios systemd (TODOS los rio-*)
sudo cp /etc/systemd/system/rio-*.service ~/backup-$(date +%Y%m%d)/ 2>/dev/null || true

# Backup NGINX (REAL: riofuturoprocesos.com)
sudo cp /etc/nginx/sites-available/riofuturoprocesos.com ~/backup-$(date +%Y%m%d)/
sudo cp /etc/nginx/sites-enabled/riofuturoprocesos.com ~/backup-$(date +%Y%m%d)/ 2>/dev/null || true

# Backup archivos .env
cp /home/debian/rio-futuro-dashboards/app/.env ~/backup-$(date +%Y%m%d)/ 2>/dev/null || true

# Backup data crítica
cp -r /home/debian/rio-futuro-dashboards/app/data ~/backup-$(date +%Y%m%d)/ 2>/dev/null || true

# Backup sessions
cp /home/debian/rio-futuro-dashboards/app/backend/data/sessions.json ~/backup-$(date +%Y%m%d)/ 2>/dev/null || true

# Comprimir backup
cd ~/
tar -czf backup-rio-dashboards-$(date +%Y%m%d-%H%M).tar.gz backup-$(date +%Y%m%d)/

# Verificar backup
ls -lh ~/backup-rio-dashboards-*.tar.gz
```
RECOMENDADO)
- [ ] NGINX config respaldado (riofuturoprocesos.com)

### 1.3 Verificar Estructura (app/ es el repo Git)
```bash
cd /home/debian/rio-futuro-dashboards/

# Ver estructura raíz
ls -la

# Verificar app/ (debe tener .git interno o ser el workdir del repo)
ls -la app/.git 2>/dev/null || ls -la .git 2>/dev/null

# Verificar app/ tiene los archivos del dashboard
ls -la app/backend/ app/pages/ app/shared/ app/Home.py 2>/dev/null

# Ver si hay duplicados en raíz
ls -la backend/ pages/ shared/ Home.py 2>/dev/null || echo "Sin duplicados en raíz"

# Verificar servicios apuntan a app/
sudo systemctl cat rio-backend.service 2>/dev/null | grep WorkingDirectory
sudo systemctl cat rio-futuro-api.service 2>/dev/null | grep WorkingDirectory
sudo systemctl cat rio-futuro-web.service 2>/dev/null | grep WorkingDirectory
```

**Checklist:**
- [ ] `app/` existe y tiene backend/, pages/, shared/
- [ ] Verificar si hay duplicados en raíz (backend/, pages/, etc.)
- [ ] Servicios apuntan a `/home/debian/rio-futuro-dashboards/app`
- [ ] `.git/` está en raíz del proyecto
- [ ] `app/shared/` existe y tiene archivos
- [ ] `app/data/` existe
- [ ] `app/.env` existe con credenciales Odoo
- [ ] `rio-backLimpiar NGINX (10 min)

### 2.1 Eliminar /reporteria/ de NGINX
```bash
# Backup antes de editar
sudo cp /etc/nginx/sites-available/riofuturoprocesos.com /tmp/nginx-backup.conf

# Editar NGINX
sudo nano /etc/nginx/sites-available/riofuturoprocesos.com

# ELIMINAR estas líneas:
# location ^~ /reporteria/ {
#     proxy_pass http://127.0.0.1:8503/reporteria/;
#     proxy_http_version 1.1;
#     proxy_set_header Upgrade $http_upgrade;
#     proxy_set_header Connection "upgrade";
#     proxy_set_header Host $host;
#     proxy_set_header X-Real-IP $remote_addr;
#     proxy_read_timeout 86400;
# }
# location = /reporteria { return 302 /reporteria/; }
```

**Checklist:**
- [ ] Backup de NGINX creado en /tmp/
- [ ] Bloques `/reporteria/` eliminados (líneas ~89-98)
- [ ] Verificar sintaxis: `sudo nginx -t`
- [ ] Recargar NGINX: `sudo systemctl reload nginx`

### 2.2 Eliminar Bloques Duplicados en NGINX
```bash
# Editar NGINX nuevamente
sudo nano /etc/nginx/sites-available/riofuturoprocesos.com

# ELIMINAR duplicados de estas secciones (aparecen 2 veces):
# - location ^~ /api/logistica/
# - location /api/
```

**Checklist:**
- [ ] Solo 1 bloque `/api/logistica/` (eliminar duplicado)
- [ ] Solo 1 bloque `/api/` (eliminar duplicado)
- [ ] `sudo nginx -t` sin errores
- [ ] `sudo systemctl reload nginx` exitoso
4: Limpiar Estructura de Archivos (15 min)

### 4.1 Verificar Estructura Actual
```bash
cd /home/debian/rio-futuro-dashboards/

# Ver TODO lo que hay
ls -lha

# Ver si existe app/
ls -lha app/ 2>/dev/null || echo "No existe app/"
```

### 4.2 Consolidar a /app/ (SI NO EXISTE)
```bash
# Solo ejecutar SI app/ NO existe y archivos están en raíz
cd /home/debian/rio-futuro-dashboards/

# Crear app/
mkdir -p app

# Mover archivos a app/
mv backend/ pages/ shared/ components/ data/ docs/ venv/ .streamlit/ app/ 2>/dev/null || true
mv Home.py Home_Content.py requirements.txt PAGES.md app/ 2>/dev/null || true
mv .env app/ 2>/dev/null || true

# Verificar
ls -lha app/
```

### 4.3 Limpiar Archivos Temporales y Duplicados
```bash
cd /home/debian/rio-futuro-dashboards/

# Eliminar archivos temporales
rm -f debug_*.py query streamlit.log nohup.out 2>/dev/null || true
rm -f app.zip 2>/dev/null || true  # 376MB

# Eliminar posibles duplicados en raíz (si app/ ya existe)
rm -rf backend/ pages/ shared/ components/ data/ docs/ venv/ .streamlit/ 2>/dev/null || true
rm -f Home.py Home_Content.py requirements.txt PAGES.md 2>/dev/null || true
```

**Checklist:**
- [ ] Archivos consolidados en `app/`
- [ ] `app.zip` eliminado (libera espacio)
- [ ] Archivos debug_*.py eliminados
- [ ] Sin duplicados en raíz

### 4.4 Verificar Estructura Final
```bash
# Listar raíz
ls -lha /home/debian/rio-futuro-dashboards/

# Verificar app/
ls -lha /home/debian/rio-futuro-dashboards/app/

# Ver espacio liberado
df -h /home/debian/
```

**Estructura esperada:**
```
/home/debian/rio-futuro-dashboards/
├── .git/                    ✅ (mantener)
├── .gitignore               ✅ (mantener)
├── app/                     ✅ (ÚNICO directorio activo)
│   ├── backend/
│   ├── pages/
│   ├── shared/
│   ├── data/
│   ├── venv5: Limpiar Servicios Systemd (5 min)

### 5.1 Eliminar TODOS los Servicios Systemd Rio
```bash
# Listar servicios existentes
ls -la /etc/systemd/system/rio-*.service

# ELIMINAR TODOS (los reemplazaremos con Docker)
sudo rm -f /etc/systemd/system/rio-backend.service
sudo rm -f /etc/systemd/system/rio-futuro-api.service
sudo rm -f /etc/systemd/system/rio-futuro-web.service

# Recargar systemd
sudo systemctl daemon-reload

# Verificar que NO quede ningún servicio rio-*
sudo systemctl list-unit-files | grep rio
```

**Checklist:**
- [ ] `rio-backend.service` eliminado
- [ ] `rio-futuro-api.service` eliminado
- [ ] `rio-futuro-web.service` eliminado
- [ ] `systemctl daemon-reload` ejecutado
- [ ] NO aparece ningún servicio rio-* al listar

**Resultado:** Todos los servicios systemd antiguos eliminados. Docker manejará los procesos.inado
- [ ] `rio-futuro-web.service` eliminado
- [ ] Solo existe `rio-backend.service`
- [ ] `systemctl daemon-reload` ejecutado sin errores

### 4.2 Renombrar rio-backend → rio-api (Consolidación)
```bash
# Detener servicio actual
sudo systemctl stop rio-backend.service
sudo systemctl disable rio-backend.service

# Crear nuevo servicio consolidado
sudo tee /etc/systemd/system/rio-api.service > /dev/null << 'EOF'
[Unit]
Description=Rio Futuro Dashboards API (FastAPI)
After=network.target

[Service]
Type=simple
User=debian
Group=debian
WorkingDirectory=/home/debian/rio-futuro-dashboards/app
Environment="PATH=/home/debian/rio-futuro-dashboards/app/venv/bin"
Environment="PYTHONPATH=/home/debian/rio-futuro-dashboards/app"
ExecStart=/home/debian/rio-futuro-dashboards/app/venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Habilitar y arrancar
sudo systemctl daemon-reload
sudo systemctl enable rio-api.service
sudo systemctl start rio-api.service

# Verificar
sudo systemctl status rio-api.service
```

**Checklist:**
- [ ] `rio-backend.service` detenido y deshabilitado
- [ ] `rio-api.service` creado
- [ ] `rio-api.service` habilitado
- [ ] `rio-api.service` corriendo (active/running)
- [ ] Puerto 8000 escuchando
- [ ] Dashboard accesible en http://SERVER_IP:8000

### 4.3 Eliminar rio-backend.service Viejo
```bash
# Eliminar servicio viejo
sudo rm -f /etc/systemd/system/rio-backend.service
sudo systemctl daemon-reload

# Verificar limpieza
sudo systemctl list-unit-files | grep rio
```

**Checklist:**
- [ ] `rio-backend.service` eliminado
- [ ] Solo existe `rio-api.service`

---

## 🌐 FASE 5: Configurar NGINX (10 min)

### 5.1 Crear Configuración NGINX para Dashboard
```bash
# Crear configuración
sudo tee /etc/nginx/sites-available/rio-futuro-dashboards > /dev/null << 'EOF'
# Rio Futuro Dashboards
# Configuración para acceso externo

upstream rio_api {
    server localhost:8000 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name dashboard.riofuturoprocesos.com;

    # Logs
    access_log /var/log/nginx/rio-dashboard-access.log;
    error_log /var/log/nginx/rio-dashboard-error.log;

    # API Backend
    location /api/ {
        proxy_pass http://rio_api;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Root - redirigir a /api/v1/docs por ahora
    location / {
        return 302 /api/v1/docs;
    }
}
EOF6: Actualizar NGINX para Docker (10 min)

### 6.1 Configurar Upstream con Failover para Blue-Green
```bash
# Editar configuración existente
sudo nano /etc/nginx/sites-available/riofuturoprocesos.com

# AGREGAR ANTES del bloque server (línea ~1):
# upstream rio_api_backend {
#     server 127.0.0.1:8000 max_fails=3 fail_timeout=30s;
#     server 127.0.0.1:8002 backup;  # DEV como backup
# }
#
# upstream rio_web_frontend {
#     server 127.0.0.1:8501 max_fails=3 fail_timeout=30s;
#     server 127.0.0.1:8502 backup;  # DEV como backup
# }
```

### 6.2 Modificar Bloques proxy_pass
```bash
# Reemplazar en location /api/:
# De: proxy_pass http://127.0.0.1:8000;
# A:  proxy_pass http://rio_api_backend;

# Reemplazar en location /dashboards/:
# De: proxy_pass http://127.0.0.1:8501/dashboards/;
# A:  proxy_pass http://rio_web_frontend/dashboards/;
```

### 6.3 Verificar y Aplicar
```bash
# Test sintaxis
sudo nginx -t

# Reload NGINX
sudo systemctl reload nginx
```

**Checklist:**
- [ ] Upstreams `rio_api_backend` y `rio_web_frontend` agregados
- [ ] Backup servers configurados (8002, 8502)
- [ ] `proxy_pass` actualizado a upstreams
- [ ] `nginx -t` exitoso
- [ ] NGINX recargado

**Resultado:** NGINX preparado para Blue-Green deployment con failover automático.
- [ ] Puerto 8001 LIBRE
- [ ] Puerto 8501 LIBRE
- [ ] Puerto 8502 LIBRE

### 6.2 Test Funcional
```bash
# Test API health
curl http://localhost:8000/health

# Test API docs
curl http://localhost:8000/api/v1/docs
```

**Checklist:**
- [ ] API responde en puerto 8000
- [ ] Heal7: Verificación Final (5 min)

### 7.2 Verificar Estructura Limpia
```bash
# Verificar raíz
ls -lha /home/debian/rio-futuro-dashboards/

# Verificar app
ls -lha /home/debian/rio-futuro-dashboards/app/

# Verificar NO hay servicios rio-*
sudo systemctl list-units --type=service --state=running | grep rio

# Verificar TODOS los puertos libres
sudo ss -tlnp | grep -E ':8000|:8001|:8501|:8502|:8503'
```

**Checklist de Estructura Final:**
```
/home/debian/rio-futuro-dashboards/
├── .git/                    ✅ (mantener)
├── .gitignore               ✅ (mantener)
├── app/                     ✅ (ÚNICO directorio activo)
│   ├── backend/
│   ├── pages/
│   ├── shared/
│   ├── data/
│   ├── venv/
│   ├── .env
│   ├── Home.py
│   └── requirements.txt
├── Dockerfile.api           ✅ (nuevo - commit pendiente)
├── Dockerfile.web           ✅ (nuevo - commit pendiente)
├── docker-compose.prod.yml  ✅ (nuevo - commit pendiente)
├── docker-compose.dev.yml   ✅ (nuevo - commit pendiente)
└── scripts/
    ├── deploy-blue-green.sh    ✅ (nuevo - commit pendiente)
    └── cleanup-old-structure.sh ✅ (ejecutado)
```

**Checklist de Puertos (TODOS LIBRES):**
- [ ] Puerto 8000 LIBRE (para Docker API PROD)
- [ ] Puerto 8001 LIBRE
- [ ] Puerto 8501 LIBRE (para Docker WEB PROD)
- [ ] Puerto 8502 LIBRE (para Docker WEB DEV)
- [ ] Puerto 8503 LIBRE
- [ ] NO hay servicios rio-* corriendo

**Checklist de NGINX:**
- [ ] `/reporteria/` eliminado ✅
- [ ] Upstreams con failover configurados ✅
- [ ] `proxy_pass` usa upstreams ✅
- [ ] Duplicados limpiados (opcional) ⏳
- [ ] `nginx -t` exitoso ✅

**Checklist de Servicios:**
- [ ] NO hay servicios rio-* habilitados
- [ ] NO hay procesos Python del dashboard corriendoklist antes de continuar
- En caso de duda, detente y consulta
- El backup es tu red de seguridad
 systemd: 2-3 (rio-backend, rio-futuro-api, rio-futuro-web)
Puertos ocupados: 8000, 8001, 8501, (8503?)
NGINX: /logistica, /api, /dashboards, /reporteria
Estructura: Duplicada o inconsistente
```

### Después de Limpieza
```
Servicios systemd: 0 (TODOS eliminados)
Puertos ocupados: 0 (TODOS libres para Docker)
NGINX: /logistica, /api, /dashboards (solo esenciales)
Estructura: Consolidada en /app/
Upstreams: Configurados con failover
```

---

## 🎯 PRÓXIMOS PASOS (Después de Limpieza)

### En Local (Windows)
```bash
cd "c:\new\RIO FUTURO\DASHBOARD\proyectos"

# Commit archivos Docker
git add Dockerfile.api Dockerfile.web
git add docker-compose.prod.yml docker-compose.dev.yml
git add scripts/deploy-blue-green.sh
git add docs/CLEANUP_CHECKLIST.md

git commit -m "Add Docker Blue-Green deployment + Cleanup checklist"
git push origin main
```

### En Servidor
```bash
cd /home/debian/rio-futuro-dashboards/app
git pull origin main

# Ejecutar deployment
chmod +x ../scripts/deploy-blue-green.sh
sudo bash ../scripts/deploy-blue-green.sh
```

**Resultado esperado:**
- ✅ Containers Docker corriendo (rio-api-prod, rio-web-prod)
- ✅ Dashboard accesible en https://riofuturoprocesos.com/dashboards/
- ✅ API accesible en https://riofuturoprocesos.com/api/
- ✅ Zero downtime deployment funcional