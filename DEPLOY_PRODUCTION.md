# Despliegue a Producción - Rio Futuro Dashboards

**Fecha de última actualización:** 14 de Enero 2026

---

## ✅ Pre-requisitos

Antes de desplegar a producción, verifica:

- [ ] Todos los tests locales pasaron
- [ ] Dev está funcionando correctamente en `https://167.114.114.51/dashboards-dev/`
- [ ] Se hizo limpieza de código (sin archivos debug, logs, o configs obsoletas)
- [ ] `permissions.json` está actualizado con todos los tabs
- [ ] `.gitignore` está configurado correctamente
- [ ] No hay secretos hardcodeados en el código

---

## 📋 Checklist de Permisos

Verificar que todos los tabs tengan entrada en `data/permissions.json`:

### Recepciones
- [x] `recepciones.kpis_calidad`
- [x] `recepciones.gestion_recepciones`
- [x] `recepciones.curva_abastecimiento`
- [x] `recepciones.aprobaciones_mp`

### Producción
- [x] `produccion.reporteria_general`
- [x] `produccion.detalle_of`
- [x] `produccion.clasificacion`

### Stock
- [x] `stock.movimientos`
- [x] `stock.camaras`
- [x] `stock.pallets`
- [x] `stock.trazabilidad`

### Finanzas
- [x] `finanzas.agrupado`
- [x] `finanzas.mensualizado`
- [x] `finanzas.ytd`
- [x] `finanzas.cg`
- [x] `finanzas.detalle`
- [x] `finanzas.flujo_caja`

### Compras
- [x] `compras.ordenes`
- [x] `compras.lineas_credito`

### Automatizaciones
- [x] `automatizaciones.crear_orden`
- [x] `automatizaciones.monitor_ordenes`
- [x] `automatizaciones.movimientos`
- [x] `automatizaciones.monitor_movimientos`

### Rendimiento
- [x] `rendimiento.trazabilidad_pallets`
- [x] `rendimiento.diagrama_sankey`

---

## 🚀 Pasos de Despliegue

### 1. Preparar repositorio

```bash
# Verificar que todo esté committeado
git status

# Ver último commit
git log -1 --oneline

# Asegurar que estamos en main
git checkout main
git pull
```

### 2. SSH al servidor

```bash
ssh debian@167.114.114.51
cd /home/debian/rio-futuro-dashboards/app
```

### 3. Backup de producción actual

```bash
# Verificar estado actual
docker ps | grep rio

# Opcional: Backup de data/permissions.json
cp data/permissions.json data/permissions.json.backup.$(date +%Y%m%d_%H%M%S)
```

### 4. Actualizar código

```bash
# Traer últimos cambios
git pull

# Verificar que se actualizó
git log -1 --oneline
```

### 5. Rebuild y despliegue

**Opción A: Sin downtime (recomendado)**

```bash
# Rebuild solo si hay cambios en Dockerfile
docker-compose -f docker-compose.prod.yml build

# Restart de containers
docker-compose -f docker-compose.prod.yml up -d
```

**Opción B: Con rebuild completo**

```bash
# Down y up con rebuild (habrá downtime de ~30s-1min)
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build
```

### 6. Verificar salud de los containers

```bash
# Ver containers corriendo
docker ps

# Verificar logs
docker logs rio-web-prod --tail 50
docker logs rio-api-prod --tail 50

# Health checks
docker inspect rio-web-prod | grep -A 5 Health
docker inspect rio-api-prod | grep -A 5 Health
```

### 7. Smoke tests

Acceder a:
- ✅ `https://riofuturoprocesos.com/dashboards/` - Home
- ✅ `https://riofuturoprocesos.com/api/health` - API health check
- ✅ Probar login
- ✅ Probar al menos un dashboard

---

## 🔍 Troubleshooting

### Container unhealthy

```bash
# Ver logs detallados
docker logs rio-web-prod --tail 100

# Reintentar
docker-compose -f docker-compose.prod.yml restart
```

### Error de baseUrlPath

Verificar en `docker-compose.prod.yml`:
```yaml
environment:
  - STREAMLIT_SERVER_BASE_URL_PATH=/dashboards
```

### Permisos no funcionan

```bash
# Verificar que permissions.json se copió correctamente
docker exec rio-web-prod cat /app/data/permissions.json | head -20
```

### API no responde

```bash
# Verificar puerto 8000
curl http://localhost:8000/health

# Ver logs
docker logs rio-api-prod --tail 100
```

---

## 🔄 Rollback

Si algo sale mal:

```bash
# Ver commits recientes
git log --oneline -5

# Volver al commit anterior
git checkout <commit-hash>

# Rebuild
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build
```

---

## 📝 Notas Post-Despliegue

- Monitorear logs por 10-15 minutos
- Verificar que no haya errores en consola del navegador
- Probar funcionalidades críticas (login, permisos, carga de data)
- Notificar al equipo que producción está actualizada

---

## 🔐 Seguridad

- **Nunca** commitear `.env` o `secrets.toml`
- Credenciales de Odoo deben estar en variables de entorno o secrets
- Revisar que `.gitignore` esté actualizado
- Mantener `permissions.json` sincronizado entre dev y prod

---

## 📞 Contacto

En caso de problemas críticos:
- **Desarrollador:** Miguel Valladares (mvalladares@riofuturo.cl)
- **Servidor:** 167.114.114.51
- **Repositorio:** https://github.com/mvalladares1/proyectos
