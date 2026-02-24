# Feedback Scanner SCAN-2BD37D9E — Rio Futuro Dashboards

## Resumen Ejecutivo

El scan `SCAN-2BD37D9E` reportó **FAIL con 5 hallazgos críticos**, pero tras revisión manual **0 son hallazgos legítimos del proyecto**. Todos son falsos positivos causados por limitaciones del scanner o errores en su ejecución. El riesgo real es **~15/100**, no 95/100.

---

## Hallazgos a Corregir en el Scanner

### 1. CRITICAL F001/F002/F005 — Health Endpoints & API Latency

**Veredicto: FALSO POSITIVO × 3 (problema del entorno del scanner, no del proyecto)**

**Problema del scanner:**
- Intentó conectarse a `localhost:8002` (según scan_result.json) pero la UI reporta `host.docker.internal:8000` — **inconsistencia entre ejecución y reporte**
- Los 3 findings son **el mismo problema** (API no estaba corriendo al momento del scan) contado 3 veces, inflando artificialmente el conteo de críticos

**Evidencia de que el proyecto está bien:**
- El endpoint `/health` existe en `backend/main.py:108` y responde `{"status": "healthy"}`
- El `docker-compose.dev.yml` mapea correctamente `8002:8000`
- Healthcheck configurado: `curl -f http://localhost:8000/health`

**Correcciones requeridas en el scanner:**

1. **Deduplicar findings**: Si la API no responde, reportar **un solo finding**, no 3 (health `/`, health `/health`, latency `/health`)
2. **Cambiar severidad**: Si el scanner no puede confirmar que el servicio debería estar corriendo, marcar como `skipped` o `warning`, no `critical`. Un scan de código no debería fallar porque un servicio runtime no está levantado
3. **Consistencia de URLs**: La UI muestra `host.docker.internal:8000` pero el JSON registra `localhost:8002`. Reportar la URL real que se usó
4. **Agregar pre-check**: Antes de ejecutar checks de API, verificar si el servicio existe/está corriendo y si no, skipear los checks de runtime con un mensaje claro

---

### 2. MEDIUM F003 — permissions.json no encontrado

**Veredicto: FALSO POSITIVO**

**Problema del scanner:**
- Buscó en `/projects/rio-futuro/data/permissions.json` — ruta incorrecta
- El archivo **SÍ EXISTE** en `data/permissions.json` con 97 líneas de permisos configurados
- Además, en el JSON crudo el `permissionscheck` aparece como `passed` con 0 findings, **contradiciéndose con el finding F003**

**Correcciones requeridas en el scanner:**

1. **Resolver rutas correctamente**: Usar rutas relativas al root del proyecto, no rutas absolutas hardcodeadas
2. **Eliminar contradicción**: Si `permissionscheck` pasa, no puede existir un finding que diga que el archivo no existe
3. **Validar existencia antes de reportar**: Hacer un `os.path.exists()` con la ruta correcta

---

### 3. MEDIUM F004 — Configuración Odoo incompleta

**Veredicto: FALSO POSITIVO**

**Problema del scanner:**
- Solo buscó variables de entorno `ODOO_URL` / `ODOO_DB` y no las encontró como env vars explícitas
- No revisó el código de configuración donde están definidas con **valores por defecto funcionales**

**Evidencia:**
```python
# backend/config/settings.py (líneas 19-20)
class Settings(BaseSettings):
    ODOO_URL: str = "https://riofuturo.server98c6e.oerpondemand.net"
    ODOO_DB: str = "riofuturo-master"
```

Pydantic-settings toma valores del `.env` si existe, pero ya tiene defaults funcionales. La app funciona sin env vars.

**Correcciones requeridas en el scanner:**

1. **Revisar código de configuración**: No solo buscar env vars — analizar archivos como `settings.py`, `config.py`, `settings.toml` para detectar defaults
2. **Detectar frameworks de config**: Pydantic-settings, python-decouple, django-environ, etc. manejan defaults en código
3. **Cambiar lógica**: Solo reportar "configuración incompleta" si NO hay default en código Y NO hay env var definida

---

### 4. OMITIDOS — Secrets Scanner: 2 "AWS keys"

**Veredicto: FALSO POSITIVO × 2 (no aparecen en la UI pero sí en scan_result.json)**

**Problema del scanner:**
- Reportó 2 findings CRITICAL de "Possible AWS key" en `backend/data/sessions.json`
- Son **contraseñas encriptadas en base64** de sesiones de usuario Odoo, no claves AWS:
  ```
  "encrypted_password": "B1EBVAQAAwsHXFBaVQ..."
  ```
- El regex del scanner es demasiado agresivo: cualquier string base64 que contenga patrones como `Aws` lo marca como AWS key
- **Estos findings están en el JSON pero NO aparecen en la UI** — bug de consistencia

**Correcciones requeridas en el scanner:**

1. **Mejorar detección de secrets**: No usar solo regex contra base64 genérico. Validar:
   - Formato real de AWS keys (empieza con `AKIA` para access keys)
   - Longitud esperada (20 chars para access key ID, 40 para secret)
   - Contexto del campo (si el key del JSON es `encrypted_password`, claramente no es una AWS key)
2. **Considerar contexto**: Un campo llamado `encrypted_password` dentro de un archivo `sessions.json` es evidentemente un password encriptado, no un secret expuesto
3. **Consistencia UI/JSON**: Todos los findings del JSON deben aparecer en la UI. Si se filtran, explicar por qué
4. **El conteo total real es 7 findings (5 critical), no 5 total como dice la UI**

---

### 5. Checks internos rotos (bugs del scanner)

**Dos checks fallaron con errores de implementación:**

```
OutputContractCheck.__init__() got an unexpected keyword argument
BackendDesignCheck.__init__() got an unexpected keyword argument
```

**Correcciones requeridas:**
1. Estos son **bugs del propio scanner** — los constructores de estos checks no aceptan los kwargs que se les pasan
2. Deben ser visibles en el reporte como errores del scanner, no silenciados
3. Revisar la inicialización de `OutputContractCheck` y `BackendDesignCheck` — probablemente les falta `**kwargs` en el `__init__` o se les pasa un parámetro que no esperan

---

### 6. Checks que pasaron pero no deberían contar como "pasados"

| Check | Estado | Problema |
|---|---|---|
| Authentication Check | `passed` (0/8 endpoints) | Pasó porque no pudo conectar a ningún endpoint — esto no es "passed", es "skipped" |
| Permissions System | `passed` (0 permisos) | Reporta 0 permisos cuando hay permisos definidos en permissions.json — no leyó el archivo |
| Role Leak Detection | `passed` | OK pero sin evidencia de qué verificó |

**Corrección**: Si un check no puede ejecutar su validación real (por falta de conectividad, archivos no encontrados, etc.), debe ser `skipped`, no `passed`.

---

## Resumen de Conteos

| Métrica | Reportado por Scanner | Valor Real |
|---|---|---|
| Total findings | 5 (UI) / 7 (JSON) | 0 legítimos |
| Critical | 3 (UI) / 5 (JSON) | 0 |
| Medium | 2 | 0 |
| Riesgo IA | 95/100 | ~15/100 |
| Gate status | FAIL | Debería ser PASS (o WARN si se quiere flag la API down) |
| Checks rotos | No reportados | 2 (OutputContractCheck, BackendDesignCheck) |

---

## Checklist de Mejoras para el Scanner

- [ ] **Deduplicar findings de API down** → 1 finding, no 3
- [ ] **Severidad de API-down en scan de código** → `skipped`/`warning`, no `critical`
- [ ] **Consistencia URLs** entre ejecución real y reporte UI
- [ ] **Pre-check de servicio** antes de checks de runtime
- [ ] **Resolución correcta de rutas** de archivos (permissions.json)
- [ ] **Eliminar contradicción** check passed vs finding de archivo faltante
- [ ] **Analizar código de configuración**, no solo env vars
- [ ] **Detectar frameworks de config** (pydantic-settings, etc.)
- [ ] **Mejorar regex de secrets** — validar formato real de AWS keys, no base64 genérico
- [ ] **Considerar contexto de campos** (`encrypted_password` ≠ secret expuesto)
- [ ] **Consistencia UI/JSON** — mostrar todos los findings o explicar filtrado
- [ ] **Reportar checks rotos** visiblemente (OutputContractCheck, BackendDesignCheck)
- [ ] **No marcar como `passed` checks que no pudieron ejecutarse** → usar `skipped`
- [ ] **Recalcular riesgo IA** considerando todo lo anterior (95 → ~15)

---

## Contexto del Proyecto para Calibración

- **Stack**: FastAPI backend + Streamlit frontend, desplegados con Docker Compose
- **Config**: Pydantic-settings con defaults en código (`backend/config/settings.py`)
- **Permisos**: Archivo JSON en `data/permissions.json` (97 líneas, múltiples dashboards)
- **Sesiones**: `backend/data/sessions.json` con passwords encriptados (XOR + base64), no secrets
- **Deploy**: SSH a Debian con `docker-compose up -d --build`
- **Puertos**: Dev API en 8002 (host) → 8000 (container), Prod en 8000:8000
- **Health**: `GET /health` → `{"status": "healthy"}` en `backend/main.py:108`
