# 🤖 BUENOBOT - Sistema de QA y Seguridad

**Versión:** 1.0.0  
**Fecha:** Febrero 2026  
**Autor:** Rio Futuro Engineering Team

---

## 📋 Índice

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Arquitectura](#arquitectura)
3. [Plan de Implementación](#plan-de-implementación)
4. [Guía de Uso](#guía-de-uso)
5. [Referencia de Checks](#referencia-de-checks)
6. [Gate Policy](#gate-policy)
7. [API Reference](#api-reference)
8. [Configuración y Deployment](#configuración-y-deployment)
9. [Seguridad](#seguridad)
10. [Extensibilidad](#extensibilidad)

---

## Resumen Ejecutivo

BUENOBOT es un sistema de control de calidad (QA) y seguridad (AppSec) diseñado específicamente para el proyecto Rio Futuro Dashboards. Actúa como un **Release Gate** automatizado que:

- ✅ Ejecuta verificaciones antes de deploy a producción
- ✅ Detecta vulnerabilidades, secretos expuestos y configuraciones inseguras
- ✅ Valida permisos y autenticación
- ✅ Mide rendimiento de endpoints
- ✅ Genera reportes accionables con Go/No-Go

### Características Principales

| Característica | Descripción |
|----------------|-------------|
| **Quick Scan** | ~2 minutos: Health, Lint, Deps, Secrets, Permisos básicos |
| **Full Scan** | ~5-10 minutos: Todo lo anterior + Tests + Performance + Infra |
| **Modelo OpenClaw** | Ejecución determinista con whitelist de comandos |
| **UI Integrada** | Página Streamlit dentro del dashboard existente |
| **API REST** | Endpoints para integración CI/CD |
| **Auditoría** | Log completo de cada ejecución |

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                     STREAMLIT UI (pages/13_BuenoBot.py)         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐  │
│  │ Ejecutar    │ │ Historial   │ │ Resultados  │ │ Config    │  │
│  │ Scan        │ │             │ │             │ │           │  │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FASTAPI BACKEND                              │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │               /buenobot Router                          │    │
│  │  POST /scan | GET /scan/{id} | GET /scans | ...         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                            │                                     │
│  ┌─────────────────────────┴─────────────────────────────┐      │
│  │                    ScanRunner                          │      │
│  │  - Orquesta ejecución de checks                       │      │
│  │  - Maneja progreso y estado                           │      │
│  │  - Calcula Gate Status                                │      │
│  └───────────────────────────┬───────────────────────────┘      │
│                              │                                   │
│  ┌───────────────────────────┴───────────────────────────┐      │
│  │                 Check Plugins                          │      │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐          │      │
│  │  │CodeQA  │ │Security│ │API QA  │ │Perms   │ ...      │      │
│  │  └────────┘ └────────┘ └────────┘ └────────┘          │      │
│  └───────────────────────────┬───────────────────────────┘      │
│                              │                                   │
│  ┌───────────────────────────┴───────────────────────────┐      │
│  │            SecureCommandRunner (Whitelist)             │      │
│  │  - Solo comandos predefinidos                         │      │
│  │  - Timeouts estrictos                                 │      │
│  │  - Sanitización de output                             │      │
│  └───────────────────────────────────────────────────────┘      │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    Storage (JSON/Disk)                   │    │
│  │  /app/data/buenobot/scans/*.json                        │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Estructura de Archivos

```
backend/
└── buenobot/
    ├── __init__.py           # Package init, exports
    ├── models.py             # Modelos Pydantic (ScanReport, Finding, etc.)
    ├── storage.py            # Persistencia JSON en disco
    ├── runner.py             # Orquestador de scans
    ├── command_runner.py     # Ejecutor seguro con whitelist
    └── checks/
        ├── __init__.py       # Registry de checks
        ├── base.py           # BaseCheck clase abstracta
        ├── code_quality.py   # RuffLint, Mypy, ImportCycles
        ├── security.py       # PipAudit, Bandit, Secrets, DockerSecurity
        ├── api_qa.py         # Health, EndpointSmoke, Auth, CORS
        ├── permissions.py    # PermissionsCheck, RoleLeakCheck
        ├── odoo_integrity.py # OdooConnectivity, OdooConfig
        ├── infra.py          # DockerStatus, Logs, Resources
        └── performance.py    # EndpointPerformance, APILatency

backend/routers/
└── buenobot.py               # FastAPI router /buenobot/*

pages/
└── 13_BuenoBot.py            # UI Streamlit

data/
└── buenobot/                 # Creado automáticamente
    ├── scans/
    │   └── {scan_id}.json    # Reportes completos
    ├── index.json            # Índice para listado rápido
    └── config.json           # Configuración
```

---

## Plan de Implementación

### Fase 1: MVP (Día 1) ✅

| Task | Descripción | Estado |
|------|-------------|--------|
| Modelos de datos | ScanReport, Finding, CheckResult | ✅ |
| SecureCommandRunner | Whitelist de comandos | ✅ |
| Storage | Persistencia JSON | ✅ |
| BaseCheck | Clase abstracta para plugins | ✅ |
| Quick Scan checks | Health, Lint, Deps, Secrets, Perms | ✅ |
| FastAPI Router | Endpoints básicos | ✅ |
| UI Streamlit | Página básica funcional | ✅ |

### Fase 2: Full Scan (Día 2)

| Task | Descripción | Estado |
|------|-------------|--------|
| Full Scan checks | Mypy, Bandit, Docker, Performance | ✅ |
| Comparación de scans | Endpoint /compare | ✅ |
| Re-run failed | Re-ejecutar checks fallidos | ✅ |
| Export Markdown | Reporte descargable | ✅ |
| Integración | Pruebas end-to-end | ⏳ |

### Fase 3: Mejoras (Futuro)

| Task | Descripción | Prioridad |
|------|-------------|-----------|
| Tests pytest | Checks de tests suite propia | P1 |
| CI/CD Integration | GitHub Actions hook | P1 |
| Notificaciones | Slack/Email al terminar | P2 |
| Scheduled scans | Cron para scans automáticos | P2 |
| PDF Export | Reporte en PDF | P3 |
| Custom checks | UI para agregar checks custom | P3 |

---

## Guía de Uso

### Desde la UI (Streamlit)

1. Navegar a la página **BUENOBOT** en el menú lateral
2. Seleccionar **Entorno** (dev/prod)
3. Seleccionar **Tipo de Scan** (Quick/Full)
4. Click en **🚀 Ejecutar Scan**
5. Observar progreso en tiempo real
6. Revisar resultados y descargar reporte

### Desde la API (CI/CD)

```bash
# Iniciar Quick Scan en dev
curl -X POST "http://localhost:8002/buenobot/scan" \
  -H "Content-Type: application/json" \
  -d '{"environment": "dev", "scan_type": "quick", "triggered_by": "ci-pipeline"}'

# Response: {"scan_id": "abc123", "status": "running", ...}

# Polling de estado
curl "http://localhost:8002/buenobot/scan/abc123/status"

# Obtener reporte completo
curl "http://localhost:8002/buenobot/scan/abc123/report"

# Obtener reporte Markdown
curl "http://localhost:8002/buenobot/scan/abc123/report?format=markdown"
```

### Interpretación de Resultados

#### Gate Status

| Status | Significado | Acción |
|--------|-------------|--------|
| ✅ **PASS** | Todo OK | Puede deployar a producción |
| ⚠️ **WARN** | Warnings encontrados | Revisar antes de deploy |
| ❌ **FAIL** | Problemas críticos | **NO DEPLOYAR** hasta resolver |

#### Severidades

| Severidad | Descripción | Gate Impact |
|-----------|-------------|-------------|
| 🔴 CRITICAL | Bloquea deploy | FAIL |
| 🟠 HIGH | Bloquea deploy | FAIL |
| 🟡 MEDIUM | Warning | WARN |
| 🔵 LOW | Informativo | - |
| ⚪ INFO | Solo información | - |

---

## Referencia de Checks

### Quick Scan Checks

| Check ID | Nombre | Descripción |
|----------|--------|-------------|
| `ruff_lint` | Ruff Linter | Análisis estático Python |
| `pip_audit` | Pip Audit | Vulnerabilidades en deps |
| `secrets_scan` | Secrets Scanner | Credenciales hardcodeadas |
| `health_check` | Health Endpoints | /health responde |
| `auth_check` | Authentication | Endpoints protegidos |
| `permissions_check` | Permissions System | permissions.json válido |
| `role_leak_check` | Role Leak Detection | Páginas sin proteger |
| `odoo_connectivity` | Odoo Connectivity | Conexión a Odoo |
| `api_latency` | API Latency | Latencia básica |

### Full Scan Checks (adicionales)

| Check ID | Nombre | Descripción |
|----------|--------|-------------|
| `mypy_check` | Mypy Type Check | Type hints validation |
| `import_check` | Import Cycles | Dependencias circulares |
| `bandit_scan` | Bandit Security | Análisis seguridad estática |
| `docker_security` | Docker Security | Config segura Docker |
| `endpoint_smoke` | Endpoint Smoke Tests | Test endpoints críticos |
| `cors_headers` | CORS & Headers | Headers de seguridad |
| `docker_status` | Docker Status | Containers running |
| `logs_check` | Error Logs | Errores recientes |
| `resources_check` | System Resources | CPU/RAM/Disk |
| `endpoint_performance` | Endpoint Performance | P95 response time |
| `odoo_config` | Odoo Client Config | Timeout/retries config |

---

## Gate Policy

### Condiciones de FAIL

El scan retorna **FAIL** si encuentra CUALQUIERA de:

1. **Secretos expuestos** - Credenciales en código
2. **Vulnerabilidades Critical/High** - En dependencias
3. **Endpoints sin auth** - Accesibles públicamente sin protección
4. **Páginas sin proteger** - Sin llamada a `proteger_pagina()`
5. **Contenedores caídos** - Docker containers no running
6. **Tests críticos fallan** - Health check no responde

### Condiciones de WARN

El scan retorna **WARN** (pero permite deploy) si:

1. **Vulnerabilidades Medium** - Revisar y planificar fix
2. **Performance degradado** - P95 > umbral
3. **Lint warnings** - Código puede mejorar
4. **Headers faltantes** - Configuración subóptima

### Condiciones de PASS

El scan retorna **PASS** si:

- Todos los checks pasan sin findings High/Critical
- Solo findings Low/Info encontrados

---

## API Reference

### Endpoints

| Method | Path | Descripción |
|--------|------|-------------|
| `POST` | `/buenobot/scan` | Iniciar nuevo scan |
| `GET` | `/buenobot/scan/{id}` | Obtener resultado completo |
| `GET` | `/buenobot/scan/{id}/status` | Estado resumido (polling) |
| `GET` | `/buenobot/scan/{id}/logs` | Logs del scan |
| `GET` | `/buenobot/scan/{id}/report` | Reporte (JSON/Markdown) |
| `GET` | `/buenobot/scans` | Listar historial |
| `POST` | `/buenobot/scan/{id}/cancel` | Cancelar scan activo |
| `GET` | `/buenobot/checks` | Listar checks disponibles |
| `GET` | `/buenobot/compare` | Comparar dos scans |
| `POST` | `/buenobot/rerun-failed/{id}` | Re-ejecutar fallidos |
| `GET` | `/buenobot/health` | Health del servicio |

### Ejemplo: POST /buenobot/scan

**Request:**
```json
{
  "environment": "dev",
  "scan_type": "quick",
  "checks": null,
  "triggered_by": "user@example.com"
}
```

**Response:**
```json
{
  "scan_id": "a1b2c3d4",
  "status": "running",
  "message": "Scan iniciado. Use GET /buenobot/scan/a1b2c3d4 para resultados.",
  "created_at": "2026-02-19T10:30:00Z"
}
```

---

## Configuración y Deployment

### Variables de Entorno

```bash
# API URLs por entorno
API_URL_DEV=http://localhost:8002
API_URL_PROD=http://localhost:8001

# Path de storage
BUENOBOT_DATA_PATH=/app/data/buenobot

# Odoo (para checks de conectividad)
ODOO_URL=https://example.odoo.com
ODOO_DB=database-name
```

### Docker Setup

BUENOBOT corre dentro del contenedor API existente. Para habilitar Docker checks desde dentro del contenedor:

```yaml
# docker-compose.dev.yml
services:
  api-dev:
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro  # Solo lectura
```

⚠️ **Seguridad:** El socket de Docker permite control total. Solo montar en read-only y en entornos controlados.

### Dependencias Adicionales

Agregar a `requirements.txt`:

```
# BUENOBOT - QA Tools
ruff>=0.1.0
pip-audit>=2.6.0
bandit>=1.7.0
filelock>=3.12.0
```

Opcionales:
```
mypy>=1.0.0      # Type checking
safety>=2.3.0    # Dependency scan alternativo
```

---

## Seguridad

### Modelo de Ejecución Seguro

BUENOBOT implementa un modelo de seguridad "OpenClaw" con las siguientes características:

1. **Whitelist de Comandos**
   - Solo comandos predefinidos en `COMMAND_WHITELIST`
   - No permite ejecución arbitraria de shell
   - Cada comando tiene timeout máximo

2. **Sanitización de Outputs**
   - Outputs truncados a 100KB
   - Patrones sensibles redactados automáticamente
   - No logs de credenciales

3. **Paths Restringidos**
   - Solo paths dentro de `/app`
   - No acceso a archivos sensibles del sistema

4. **Auditoría**
   - Log de cada ejecución con timestamp
   - Usuario que inició el scan
   - Commit SHA para trazabilidad

### Comandos Permitidos

Ver `backend/buenobot/command_runner.py` para la lista completa:

```python
COMMAND_WHITELIST = {
    "ruff_check": ...,      # Lint
    "pip_audit": ...,       # Security
    "git_rev_parse": ...,   # Git info
    "docker_ps": ...,       # Docker status
    "disk_usage": ...,      # System info
    ...
}
```

### Consideraciones para CI/CD

- El endpoint `/buenobot/scan` no requiere autenticación actualmente
- Para producción, agregar middleware de auth en el router
- Limitar rate de scans para evitar DoS

---

## Extensibilidad

### Agregar un Nuevo Check

1. Crear clase en el directorio `checks/`:

```python
# backend/buenobot/checks/custom.py
from .base import BaseCheck, CheckRegistry
from ..models import CheckResult, CheckCategory, CheckSeverity

@CheckRegistry.register("mi_check", quick=True, full=True)
class MiCustomCheck(BaseCheck):
    name = "Mi Check Custom"
    category = CheckCategory.CODE_QUALITY
    description = "Descripción del check"
    
    async def run(self) -> CheckResult:
        self.log("Ejecutando mi check...")
        
        # Lógica del check...
        
        if problema_encontrado:
            self.add_finding(
                title="Problema detectado",
                description="Descripción detallada",
                severity=CheckSeverity.MEDIUM,
                recommendation="Cómo solucionarlo"
            )
            return self._create_result("failed", "Resumen")
        
        return self._create_result("passed", "Todo OK")
```

2. Importar en `checks/__init__.py`:

```python
from .custom import MiCustomCheck
```

3. El check se registra automáticamente y aparece en los scans.

### Agregar un Nuevo Comando

Si el check necesita ejecutar un comando externo:

1. Agregar a `COMMAND_WHITELIST` en `command_runner.py`:

```python
"mi_comando": AllowedCommand(
    name="mi_comando",
    command=["mi-herramienta", "--flag"],
    category=CommandCategory.LINT,
    timeout=60,
    description="Qué hace"
)
```

2. Usar en el check:

```python
result = await self.command_runner.run("mi_comando", extra_args=["path/"])
```

---

## Troubleshooting

### El scan no inicia

1. Verificar que el API esté running: `curl http://localhost:8002/health`
2. Verificar logs del contenedor: `docker logs rio-api-dev`
3. Verificar permisos del directorio `/app/data/buenobot`

### Check específico falla siempre

1. Verificar que la herramienta esté instalada (ruff, pip-audit, etc.)
2. Revisar logs del scan para error específico
3. El check puede marcarse como "skipped" si la herramienta no está

### Docker checks fallan

1. Verificar que el socket Docker esté montado
2. Verificar permisos: el usuario del contenedor debe poder acceder al socket

---

## Changelog

### v1.0.0 (Febrero 2026)

- ✨ Release inicial
- Implementación de Quick Scan y Full Scan
- 15 checks cubriendo Code Quality, Security, API QA, Permissions, Odoo, Infra, Performance
- UI Streamlit completa
- API REST con todos los endpoints
- Reportes en JSON y Markdown

---

*Documentación generada para BUENOBOT v1.0.0*
