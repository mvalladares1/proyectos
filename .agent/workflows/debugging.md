---
description: Estándar de debugging para el proyecto Dashboard Rio Futuro
---

# Estándares de Debugging

Este documento describe las prácticas recomendadas para realizar debugging en el proyecto siguiendo los estándares de la industria.

**Última actualización:** 07 de Enero 2026

---

## 1. Uso del Módulo `logging` de Python

En lugar de usar `print()`, utiliza el módulo `logging` estándar de Python:

```python
import logging

# Configuración básica al inicio del archivo
logger = logging.getLogger(__name__)

# Niveles de logging (de menor a mayor severidad):
logger.debug("Información detallada para diagnóstico")
logger.info("Confirmación de que las cosas funcionan")
logger.warning("Algo inesperado, pero el programa sigue funcionando")
logger.error("Error que impide ejecutar alguna función")
logger.critical("Error grave que puede detener el programa")
```

## 2. Configuración Centralizada del Logging

Configura el logging en un archivo central (ej: `config/logging_config.py`):

```python
import logging
import os

def setup_logging():
    level = logging.DEBUG if os.getenv("DEBUG") == "true" else logging.INFO
    
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
```

## 3. Variables de Entorno para Control

Usa variables de entorno para habilitar/deshabilitar debug:

```bash
# En .env
DEBUG=true
LOG_LEVEL=DEBUG
```

```python
# En el código
import os
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

if DEBUG:
    logger.debug(f"Datos recibidos: {data}")
```

## 4. Archivos de Debug Temporales

Si necesitas crear scripts de debug temporales:

1. **Nombrarlos claramente**: `debug_nombre_funcionalidad.py`
2. **Documentar su propósito** al inicio del archivo
3. **Eliminarlos antes de hacer commit** a la rama principal
4. **Añadirlos a `.gitignore`** si son solo locales:
   ```
   debug_*.py
   ```

## 5. Buenas Prácticas

### ✅ Hacer:
- Usar logging en lugar de print
- Configurar niveles apropiados (DEBUG vs INFO vs ERROR)
- Incluir contexto útil en los mensajes
- Usar f-strings para formatear mensajes de log
- Limpiar código de debug antes de merge a producción

### ❌ Evitar:
- Dejar `print()` en código de producción
- Loggear información sensible (contraseñas, tokens)
- Loggear en loops muy frecuentes sin control
- Dejar archivos `debug_*.py` en el repositorio

## 6. Ejemplo de Implementación Correcta

```python
import logging
import os

logger = logging.getLogger(__name__)

class MiServicio:
    def procesar_datos(self, datos):
        logger.debug(f"Iniciando procesamiento de {len(datos)} registros")
        
        try:
            resultado = self._transformar(datos)
            logger.info(f"Procesados {len(resultado)} registros exitosamente")
            return resultado
        except Exception as e:
            logger.error(f"Error procesando datos: {e}", exc_info=True)
            raise
```

## 7. Debugging en Streamlit

Para aplicaciones Streamlit, usa `st.write()` o `st.text()` para debug visual:

```python
import streamlit as st
import os

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

if DEBUG:
    with st.expander("🔍 Debug Info"):
        st.json(data)
```

## 8. Herramientas Recomendadas

- **VS Code Debugger**: Para debugging interactivo
- **Docker logs**: `docker logs <container> --tail 50 -f`
- **NGINX logs**: `sudo tail -f /var/log/nginx/error.log`
- **Python debugger**: `import pdb; pdb.set_trace()`

---

## 9. Debugging Docker

### Containers

```bash
# Ver logs en tiempo real
docker logs rio-api-prod --tail 50 -f

# Ejecutar comandos dentro del container
docker exec rio-api-prod curl http://localhost:8000/health

# Inspeccionar configuración
docker inspect rio-api-prod | grep -A 10 Env
docker inspect rio-web-prod --format='{{.NetworkSettings.IPAddress}}'

# Ver procesos
docker top rio-web-prod
```

### Network Issues

```bash
# Verificar conectividad container-to-host
docker exec rio-web-prod curl -v http://127.0.0.1:8000/health

# Inspeccionar red
docker network inspect rio-network

# Puertos escuchando en host
ss -tlnp | grep -E '(8000|8002|8501|8502)'

# Test desde host
curl http://127.0.0.1:8501
curl http://127.0.0.1:8502
```

### Common Issues

**"No se puede conectar al servidor API"**:
- ✅ Verificar `API_URL` en variables de entorno
- ✅ Container web debe usar `network_mode: "host"` 
- ✅ NO usar IPs de containers (172.x.x.x) desde bridge network
- ✅ Usar `127.0.0.1` en lugar de `localhost`

**Container reiniciando constantemente**:
- Ver logs: `docker logs <container> --tail 100`
- Verificar healthcheck: `docker inspect <container> | grep -A 10 Health`
- Revisar variables de entorno

---

## 10. Debugging NGINX

```bash
# Validar sintaxis
sudo nginx -t

# Ver configuración activa
sudo nginx -T | grep -A 20 "server_name riofuturoprocesos"

# Logs en tiempo real
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Reload sin downtime
sudo systemctl reload nginx

# Test conectividad a upstreams
curl -I http://127.0.0.1:8000/health  # API
curl -I http://127.0.0.1:8501         # Web
```

### Common NGINX Issues

**Error 502 Bad Gateway**:
- Backend no está escuchando en el puerto esperado
- Verificar: `ss -tlnp | grep 8000`

**Error 521 (Cloudflare)**:
- SSL/TLS mismatch entre Cloudflare y origen
- Verificar certificados en `/etc/nginx/ssl/`

**404 en endpoints**:
- Revisar `proxy_pass` trailing slash
- Correcto: `proxy_pass http://backend/;` (con /)
- Incorrecto: `proxy_pass http://backend;` (sin /)

---

## 11. Scripts de Debug

Los scripts `debug_*.py` deben:
- Nombrarlos claramente: `debug_nombre_funcionalidad.py`
- Documentar su propósito al inicio
- **NO hacer commit** a la rama principal
- Agregarse a `.gitignore`

Ejemplo:
```python
"""
Debug script para probar conectividad API desde Streamlit container
Uso: docker exec rio-web-prod python debug_api_connection.py
"""
import httpx
import os

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

try:
    response = httpx.get(f"{API_URL}/health", timeout=5.0)
    print(f"✅ API responde: {response.status_code}")
    print(f"Body: {response.text}")
except Exception as e:
    print(f"❌ Error: {e}")
```

---

## 12. Checklist de Troubleshooting

Antes de pedir ayuda, verificar:

- [ ] Logs del container: `docker logs <container> --tail 50`
- [ ] Container está running: `docker ps`
- [ ] Healthcheck status: `docker ps --format 'table {{.Names}}\t{{.Status}}'`
- [ ] Variables de entorno: `docker exec <container> env | grep API_URL`
- [ ] Conectividad interna: `docker exec <container> curl localhost:8000`
- [ ] Puertos escuchando: `ss -tlnp | grep <puerto>`
- [ ] NGINX syntax: `sudo nginx -t`
- [ ] NGINX logs: `sudo tail /var/log/nginx/error.log`

---

## 13. Herramientas Recomendadas

- **pdb/ipdb**: Debugger interactivo de Python
- **debugpy**: Para debugging remoto (VS Code)
- **rich**: Para logging con formato enriquecido en terminal
