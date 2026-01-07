# 🚀 Guía Rápida de Deployment

**Última actualización**: 2026-01-07

---

## 📋 TL;DR - Comandos Esenciales

### Deploy a DEV (Probar cambios)
```powershell
ssh debian@167.114.114.51 "cd /home/debian/rio-futuro-dashboards/app && git pull && docker-compose -f docker-compose.dev.yml up -d --build"
```
**Verificar**: https://riofuturoprocesos.com/dashboards-dev/

---

### Deploy a PROD (Publicar)
```powershell
ssh debian@167.114.114.51 "cd /home/debian/rio-futuro-dashboards/app && git pull && docker-compose -f docker-compose.prod.yml up -d --build"
```
**Verificar**: https://riofuturoprocesos.com/dashboards/

---

## 🔄 Workflow Completo

### ⚠️ IMPORTANTE: Un Solo Repositorio

**NO necesitas git separado para DEV y PROD**:
- ✅ Ambos usan el mismo repo: `main` branch
- ✅ Mismo código fuente en `/home/debian/rio-futuro-dashboards/app`
- ✅ La diferencia es solo el archivo docker-compose que ejecutas
- ✅ Un solo `git pull` actualiza ambos entornos

**Cómo funciona**:
```
GitHub (main) 
    ↓ git pull
Servidor: /home/debian/rio-futuro-dashboards/app
    ├─→ docker-compose -f docker-compose.dev.yml   (DEV: puertos 8002, 8502)
    └─→ docker-compose -f docker-compose.prod.yml  (PROD: puertos 8000, 8501)
```

---

### 1. Desarrollo Local
```powershell
# En tu máquina Windows
cd 'c:\new\RIO FUTURO\DASHBOARD\proyectos'

# Hacer cambios en código
code .  # Editar archivos

# Commit y push a main
git add .
git commit -m "Feature: descripción del cambio"
git push origin main
```

**Listo**: Cambios están en GitHub, listos para deploy a DEV o PROD

---

### 2. Probar en DEV
```powershell
# Deploy automático a DEV
ssh debian@167.114.114.51 "cd /home/debian/rio-futuro-dashboards/app && git pull && docker-compose -f docker-compose.dev.yml up -d --build"
```

**¿Qué pasa?**
- ✅ Descarga código de GitHub
- ✅ Reconstruye imágenes Docker
- ✅ Reinicia containers DEV (puertos 8002, 8502)
- ⏱️ Tiempo: ~2-3 minutos

**Verificar**:
- Abrir: https://riofuturoprocesos.com/dashboards-dev/
- Login y probar funcionalidad
- Si hay errores: ver logs

```bash
# Ver logs en tiempo real
ssh debian@167.114.114.51
docker logs rio-web-dev -f
```

---

### 3. Publicar en PROD

**⚠️ Solo después de verificar en DEV**

```powershell
# Deploy a PROD
ssh debian@167.114.114.51 "cd /home/debian/rio-futuro-dashboards/app && git pull && docker-compose -f docker-compose.prod.yml up -d --build"
```

**Impacto**:
- ⏱️ Downtime: 30-60 segundos
- 👥 Usuarios desconectados temporalmente
- 🔄 Sesiones se preservan (cookies)

**Verificar**:
- Abrir: https://riofuturoprocesos.com/dashboards/
- Probar funcionalidades críticas
- Revisar logs si hay problemas

---

## ⚡ Deploy Sin Downtime

Para cambios críticos:

```bash
ssh debian@167.114.114.51
cd /home/debian/rio-futuro-dashboards/app

# 1. Actualizar y rebuild DEV
git pull
docker-compose -f docker-compose.dev.yml up -d --build

# 2. Verificar DEV
curl http://127.0.0.1:8502
docker logs rio-api-dev --tail 20

# 3. Cambiar tráfico a DEV (manual)
sudo sed -i 's/127.0.0.1:8000 max_fails=3/127.0.0.1:8000 down/' /etc/nginx/sites-available/riofuturoprocesos.com
sudo systemctl reload nginx

# 4. Rebuild PROD tranquilo
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build

# 5. Restaurar tráfico a PROD
sudo sed -i 's/127.0.0.1:8000 down/127.0.0.1:8000 max_fails=3/' /etc/nginx/sites-available/riofuturoprocesos.com
sudo systemctl reload nginx
```

---

## 🔙 Rollback

**Si algo sale mal en PROD**:

```bash
ssh debian@167.114.114.51
cd /home/debian/rio-futuro-dashboards/app

# Ver commits recientes
git log --oneline -5

# Volver a commit anterior
git reset --hard <commit-hash>

# Rebuild PROD con código anterior
docker-compose -f docker-compose.prod.yml up -d --build
```

**Failover automático**:
- Si PROD falla (healthcheck), NGINX automáticamente usa DEV
- No requiere intervención manual
- Ver: `docker ps` (si unhealthy, failover activo)

---

## 🐛 Troubleshooting

### Container no arranca

```bash
# Ver logs
docker logs rio-web-prod --tail 100
docker logs rio-api-prod --tail 100

# Ver estado
docker ps -a --filter name=rio-

# Rebuild forzado
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build --force-recreate
```

### Error "No se puede conectar al servidor API"

```bash
# Verificar conectividad
docker exec rio-web-prod curl http://127.0.0.1:8000/health

# Ver variables de entorno
docker exec rio-web-prod env | grep API_URL
# Debe ser: API_URL=http://127.0.0.1:8000

# Recrear container
docker-compose -f docker-compose.prod.yml up -d --force-recreate web-prod
```

### NGINX 502 Bad Gateway

```bash
# Verificar upstreams
curl http://127.0.0.1:8000/health  # Debe responder
curl http://127.0.0.1:8501          # Debe responder

# Ver logs NGINX
sudo tail -f /var/log/nginx/error.log

# Test config
sudo nginx -t

# Reload
sudo systemctl reload nginx
```

---

## 📊 Verificación Post-Deploy

```bash
# Conectar al servidor
ssh debian@167.114.114.51

# Estado general
docker ps --format 'table {{.Names}}\t{{.Status}}'

# Health checks
curl http://127.0.0.1:8000/health  # ✅ {"status":"healthy"}
curl http://127.0.0.1:8002/health  # ✅ {"status":"healthy"}

# Logs (últimas líneas)
docker logs rio-api-prod --tail 20
docker logs rio-web-prod --tail 20
```

**Señales de éxito**:
- ✅ Status: `Up X minutes (healthy)` o `Up X minutes`
- ✅ API health: `{"status":"healthy"}`
- ✅ Dashboard carga sin errores
- ✅ Login funciona

---

## 🎯 Mejores Prácticas

1. **Siempre probar en DEV primero**
   - Deploy a DEV → Verificar → Deploy a PROD

2. **Deploy en horarios de bajo tráfico**
   - Preferible fuera de horario laboral
   - Minimiza impacto en usuarios

3. **Commits descriptivos**
   - `git commit -m "Fix: error en cálculo de rendimiento"`
   - `git commit -m "Feature: nuevo dashboard de compras"`

4. **Verificar antes de cerrar**
   - Abrir el dashboard
   - Probar funcionalidad modificada
   - Revisar logs por errores

5. **Comunicar cambios importantes**
   - Avisar a usuarios si hay downtime
   - Documentar cambios en changelog

---

## 📁 Archivos Clave

| Archivo | Propósito |
|---------|-----------|
| `docker-compose.prod.yml` | Config PROD (8000, 8501) |
| `docker-compose.dev.yml` | Config DEV (8002, 8502) |
| `Dockerfile.api` | Build backend FastAPI |
| `Dockerfile.web` | Build frontend Streamlit |
| `riofuturoprocesos.com.nginx` | Config NGINX local |
| `/etc/nginx/sites-available/riofuturoprocesos.com` | Config NGINX servidor |

---

## 🔗 Links Útiles

- **PROD**: https://riofuturoprocesos.com/dashboards/
- **DEV**: https://riofuturoprocesos.com/dashboards-dev/
- **Logística**: https://riofuturoprocesos.com/logistica/
- **Repo**: https://github.com/mvalladares1/proyectos

---

## 📞 Ayuda

**Documentación completa**: `.agent/workflows/docker-deployment.md`

**Logs importantes**:
```bash
docker logs rio-api-prod --tail 100    # API PROD
docker logs rio-web-prod --tail 100    # Web PROD
docker logs rio-api-dev --tail 100     # API DEV
docker logs rio-web-dev --tail 100     # Web DEV
sudo tail -100 /var/log/nginx/error.log # NGINX
```
