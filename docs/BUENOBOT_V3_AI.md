# BUENOBOT v3.0 - Motor Inteligente de Validación Backend-Aware

## Resumen Ejecutivo

BUENOBOT v3.0 introduce un **motor de análisis híbrido de IA** que complementa las validaciones determinísticas existentes. El sistema puede usar un LLM local (Ollama/LMStudio) para análisis básicos o escalar a OpenAI API para casos críticos, manteniendo siempre el **gate PASS/WARN/FAIL determinístico**.

## Arquitectura v3.0

```
┌─────────────────────────────────────────────────────────────┐
│                    BUENOBOT v3.0                            │
├─────────────────────────────────────────────────────────────┤
│  Scan Runner                                                │
│  ├── Ejecuta 15+ checks determinísticos                    │
│  ├── Calcula Gate Status (PASS/WARN/FAIL)                  │
│  └── Invoca AI Gateway post-scan                           │
├─────────────────────────────────────────────────────────────┤
│  AI Gateway                                                 │
│  ├── EvidencePack Builder (sanitización, límites)          │
│  ├── AI Router (selección de motor)                        │
│  │   ├── Mock Engine (desarrollo)                          │
│  │   ├── Local Engine (Ollama HTTP)                        │
│  │   └── OpenAI Engine (API)                               │
│  └── AI Cache (por commit_sha + evidence_hash)             │
├─────────────────────────────────────────────────────────────┤
│  Output                                                     │
│  ├── ScanReportV3 (incluye AIAnalysisResult)               │
│  ├── Root Causes identificados                              │
│  ├── Recommendations con código                             │
│  └── Risk Score (0-100) + Confidence                        │
└─────────────────────────────────────────────────────────────┘
```

## Principios de Diseño

1. **Gate determinístico**: La decisión PASS/WARN/FAIL se basa en reglas fijas (OpenClaw). La IA NO cambia el gate, solo explica y sugiere.

2. **Híbrido económico**: Usar motor local siempre que sea posible. Escalar a OpenAI solo para casos críticos/complejos.

3. **Cache inteligente**: Cachear respuestas de IA por commit_sha para evitar costos repetidos.

4. **Sanitización**: NUNCA enviar credenciales o datos sensibles a la IA.

## Componentes Nuevos

### 1. AI Gateway (`backend/buenobot/ai/gateway.py`)

Orquestador principal que:
- Valida si AI está habilitada
- Construye EvidencePack sanitizado
- Selecciona motor apropiado
- Maneja cache
- Retorna AIEnrichedReport

### 2. AI Router (`backend/buenobot/ai/router.py`)

Decide entre motores basado en:
- Severidad de findings (CRITICAL → OpenAI)
- Triggers de complejidad (SQL injection, password leak → OpenAI)
- Modo de análisis (deep → OpenAI)
- Configuración por defecto

### 3. Local Engine (`backend/buenobot/ai/local_engine.py`)

Motor local que soporta:
- **Modo mock**: Genera respuestas inteligentes basadas en triggers
- **Modo HTTP**: Llama a Ollama/LMStudio via API

### 4. OpenAI Engine (`backend/buenobot/ai/openai_engine.py`)

Motor de API con:
- Respuestas JSON estructuradas
- Sanitización de requests/responses
- Manejo de errores y timeouts

### 5. EvidencePack Builder (`backend/buenobot/evidence.py`)

Construye paquetes de evidencia con:
- Límite de findings (max 20)
- Sanitización de datos sensibles
- Hash para cache
- Métricas y metadata

### 6. AI Cache (`backend/buenobot/cache_ai.py`)

Cache de respuestas IA:
- Key: commit_sha + evidence_hash + engine
- TTL configurable (default 24h)
- Estadísticas y limpieza

## Nuevos Endpoints API

```
GET  /buenobot/scan/{id}/ai          - Obtener análisis IA
POST /buenobot/scan/{id}/ai/reanalyze - Re-analizar con IA
GET  /buenobot/ai/config             - Ver configuración IA
GET  /buenobot/ai/cache/stats        - Stats del cache
POST /buenobot/ai/cache/clear        - Limpiar cache
```

## Configuración

Variables de entorno:

```env
# Habilitar IA
BUENOBOT_AI_ENABLED=true

# Motor por defecto (mock, local, openai)
BUENOBOT_DEFAULT_ENGINE=mock

# OpenAI (opcional)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Motor local (Ollama)
BUENOBOT_LOCAL_ENGINE_URL=http://localhost:11434
BUENOBOT_LOCAL_ENGINE_MODE=mock  # o "http"
BUENOBOT_LOCAL_ENGINE_MODEL=llama2

# Cache
BUENOBOT_CACHE_ENABLED=true
BUENOBOT_CACHE_TTL_HOURS=24

# Routing
BUENOBOT_USE_API_FOR_CRITICAL=true
BUENOBOT_USE_API_FOR_COMPLEX=true
```

## Mejoras en BackendDesignCheck

El check de diseño backend ahora detecta correctamente:

```python
# DETECTA (CRÍTICO):
password: str = Query(...)
secret_key: str = Query(...)

# DETECTA (HIGH):
username: str = Query(...)
```

## Issue Real Detectado

En `backend/routers/recepcion.py`:
- Línea 17-18: `username` y `password` como Query params
- Línea 36: print() statement en router

Estos issues serán reportados como CRITICAL por el BackendDesignCheck y causarán FAIL en el gate.

## Flujo de Scan v3.0

1. Usuario inicia scan (Quick/Full)
2. Runner ejecuta checks determinísticos
3. Runner calcula Gate Status (PASS/WARN/FAIL)
4. Runner invoca AI Gateway
5. AI Gateway construye EvidencePack
6. AI Router selecciona motor
7. Motor genera análisis
8. Resultado se cachea
9. AIAnalysisResult se añade al reporte
10. UI muestra análisis IA con recommendations

## UI Streamlit

Nueva sección "AI Analysis" que muestra:
- Motor usado y tiempo de análisis
- Risk Score (0-100) y Confianza
- Summary generado por IA
- Root Causes con explicaciones
- Recommendations con código ejemplo
- Botón "Re-analizar con IA (Deep)"

## Próximos Pasos

1. **Integrar Ollama**: Configurar `BUENOBOT_LOCAL_ENGINE_MODE=http` cuando Ollama esté disponible
2. **Agregar OpenAI Key**: Para análisis deep de issues críticos
3. **Crear más contracts**: YAML contracts para otros endpoints
4. **Métricas**: Agregar prometheus metrics para AI usage
5. **CI/CD Integration**: Hook para ejecutar BUENOBOT en cada PR

## Archivos Modificados/Creados

### Nuevos:
- `backend/buenobot/config.py` - Configuración de IA
- `backend/buenobot/evidence.py` - EvidencePack builder
- `backend/buenobot/cache_ai.py` - Cache de IA
- `backend/buenobot/ai/__init__.py` - Módulo AI
- `backend/buenobot/ai/gateway.py` - AI Gateway
- `backend/buenobot/ai/router.py` - AI Router
- `backend/buenobot/ai/local_engine.py` - Motor local
- `backend/buenobot/ai/openai_engine.py` - Motor OpenAI
- `backend/buenobot/ai/prompts/*.md` - Prompts de IA
- `backend/buenobot/contracts/*.yaml` - Contracts YAML

### Modificados:
- `backend/buenobot/models.py` - Añadido AIAnalysisResult, ScanReportV3
- `backend/buenobot/runner.py` - Integración AI post-scan
- `backend/buenobot/checks/backend_design.py` - Mejorado password detection
- `backend/routers/buenobot.py` - Nuevos endpoints v3
- `pages/13_BuenoBot.py` - UI con AI analysis
