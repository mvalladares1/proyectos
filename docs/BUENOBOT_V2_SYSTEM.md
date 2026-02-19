# BUENOBOT v2.0 - Motor Inteligente de Validación Backend-Aware

## Resumen Ejecutivo

BUENOBOT v2.0 es un sistema de QA/AppSec/Release Gate diseñado para validación automatizada
de calidad y seguridad antes de deploys a producción. Evoluciona de un ejecutor de herramientas
hacia un **motor inteligente de validación backend-aware**.

### Características Principales v2.0

| Feature | Descripción | Estado |
|---------|-------------|--------|
| Output Contract Testing | Validación YAML de respuestas API | ✅ Implementado |
| Backend Design Analysis | Análisis AST de código Python | ✅ Implementado |
| Dynamic Filter Validation | Verificación que filtros se apliquen | ✅ Implementado |
| Gate Policy v2 | Reglas estrictas de seguridad | ✅ Implementado |
| Security Hardening | Sanitización logs/outputs | ✅ Implementado |
| Enhanced Evidence | Modelo rico de evidencias | ✅ Implementado |

---

## Arquitectura v2.0

```
backend/buenobot/
├── __init__.py              # v2.0.0 exports
├── models.py                # Modelos Pydantic + EnhancedFinding
├── storage.py               # Persistencia JSON
├── runner.py                # Orquestador async
├── command_runner.py        # SecureCommandRunner v2 con hardening
├── security.py              # SecuritySanitizer, InputValidator, AuditLogger
│
├── contracts/               # 🆕 Sistema de contratos
│   ├── __init__.py
│   ├── schema.py           # ContractRule, EndpointContract, Registry
│   ├── rules.py            # RuleEvaluator + 15 tipos de reglas
│   ├── validator.py        # ContractValidator
│   └── definitions/        # Contratos YAML
│       └── api_contracts.yaml
│
└── checks/                  # 18 checks en 7 categorías
    ├── base.py              # BaseCheck + CheckRegistry
    ├── code_quality.py      # Ruff, Mypy
    ├── security.py          # PipAudit, Bandit, Secrets
    ├── api_qa.py            # Health, Smoke, Auth, CORS
    ├── permissions.py       # Permisos Odoo
    ├── odoo_integrity.py    # Conectividad Odoo
    ├── infra.py             # Docker, Logs, Resources
    ├── performance.py       # Latency checks
    ├── output_qa.py         # 🆕 OutputContractCheck, FilterValidationCheck
    └── backend_design.py    # 🆕 BackendDesignCheck (AST)
```

---

## 1. Output Contract Testing

### Concepto

Define contratos YAML que especifican qué debe cumplir cada respuesta de endpoint.
Cuando un endpoint viola su contrato, se genera un finding de seguridad/calidad.

### Estructura de Contrato YAML

```yaml
contracts:
  - endpoint: /api/v1/stock/camaras
    method: GET
    description: Stock agrupado por cámaras
    
    rules:
      # Regla: No fechas futuras
      - rule_type: no_future_dates
        field_path: "$.data[*].ultima_actualizacion"
        severity: medium
        
      # Regla: Cantidades no negativas  
      - rule_type: no_negative_values
        field_path: "$.data[*].cantidad_total"
        severity: high
        
      # Regla: Sin credenciales en output (CRÍTICO)
      - rule_type: no_credentials_in_output
        field_path: "$"
        severity: critical
    
    # Validación de filtros
    filter_validations:
      - filter_param: fecha_desde
        filter_type: gte
        response_field: "$.data[*].fecha_ingreso"
```

### Tipos de Reglas Disponibles

| Rule Type | Descripción | Params |
|-----------|-------------|--------|
| `date_in_range` | Fechas dentro de rango | `min_date`, `max_date`, `days_back`, `days_forward` |
| `no_future_dates` | Sin fechas futuras | `tolerance_days` |
| `allowed_values` | Valores en lista permitida | `values` |
| `allowed_values_if` | Valores condicionales | `if_field`, `if_values`, `then_allowed` |
| `not_null` | Campo no puede ser null | - |
| `no_negative_values` | Sin valores negativos | `allow_zero` |
| `subset_of_param` | Valores deben estar en param enviado | `param_name` |
| `respects_filter` | Resultados respetan filtro | `filter_param`, `filter_type` |
| `sum_equals` | Suma de valores igual a esperado | `expected`, `tolerance` |
| `monotonic_sequence` | Secuencia creciente/decreciente | `direction` |
| `fields_present` | Campos requeridos presentes | `required` |
| `array_not_empty` | Arrays no vacíos | - |
| `unique_values` | Sin duplicados | - |
| `no_credentials_in_output` | Sin credenciales expuestas | - |

### Agregar Nuevos Contratos

1. Crear/editar archivo en `backend/buenobot/contracts/definitions/`
2. Seguir schema YAML documentado
3. Ejecutar scan para validar

---

## 2. Backend Design Analyzer (AST)

### Concepto

Analiza código Python usando AST para detectar antipatrones de diseño y seguridad
**sin ejecutar** el código.

### Reglas Implementadas

| Rule | Severidad | Descripción |
|------|-----------|-------------|
| `password_in_query_params` | CRITICAL | Detecta password/token en Query() params |
| `hardcoded_credentials` | CRITICAL | Variables con credenciales hardcodeadas |
| `sql_injection_risk` | HIGH | f-strings/concatenación en queries |
| `mutative_get` | HIGH | Operaciones de escritura en endpoints GET |
| `print_in_routers` | LOW | print() en archivos de router |
| `generic_exception` | MEDIUM | except Exception sin especificar |

### Ejemplo de Detección

```python
# DETECTADO: password_in_query_params
@router.get("/data")
async def get_data(
    username: str = Query(...),
    password: str = Query(...)  # ⚠️ CRITICAL: password en query
):
    ...

# DETECTADO: mutative_get
@router.get("/users/{id}")  
async def get_user(id: int):
    service.delete_user(id)  # ⚠️ HIGH: operación mutativa en GET
    ...
```

---

## 3. Gate Policy v2.0

### Reglas de Bloqueo Automático

El gate ahora **FALLA automáticamente** si detecta:

1. **Credenciales en Query Params** → FAIL
2. **Credenciales expuestas en Output** → FAIL  
3. **Filtros no respetados** (data leak) → FAIL
4. **SQL Injection Risk** → FAIL
5. **Vulnerabilidades CRITICAL/HIGH** → FAIL

### Flujo de Evaluación

```
┌─────────────────────────────────────────────────┐
│               Gate Policy v2.0                   │
├─────────────────────────────────────────────────┤
│                                                  │
│  1. Buscar gate-breakers (reglas críticas)      │
│     └── password_in_query_params?               │
│     └── no_credentials_in_output?               │
│     └── respects_filter? (filtros violados)     │
│     └── sql_injection_risk?                     │
│                                                  │
│  2. Si hay gate-breakers → FAIL inmediato       │
│                                                  │
│  3. Si no, evaluar por severidad:               │
│     └── CRITICAL findings? → FAIL               │
│     └── HIGH findings? → FAIL                   │
│     └── MEDIUM findings? → WARN                 │
│     └── Solo LOW/INFO? → PASS                   │
│                                                  │
│  4. Generar checklist Go/No-Go                  │
│     ✓ sin_credenciales_expuestas               │
│     ✓ sin_vulnerabilidades_criticas            │
│     ✓ filtros_funcionando                       │
│     ✓ codigo_sin_errores_criticos              │
│     ✓ api_respondiendo                          │
│     ✓ permisos_correctos                        │
│                                                  │
└─────────────────────────────────────────────────┘
```

---

## 4. Security Hardening

### SecuritySanitizer

Sanitiza automáticamente:
- Diccionarios con campos sensibles
- Strings con tokens/passwords
- Logs de ejecución

```python
from backend.buenobot.security import get_sanitizer

sanitizer = get_sanitizer()

# Sanitizar dict
safe_data = sanitizer.sanitize_dict({
    "user": "admin",
    "password": "secret123",  # → "***REDACTED***"
    "api_key": "sk-abc123"    # → "***REDACTED***"
})

# Sanitizar string
safe_log = sanitizer.sanitize_string(
    'token="eyJhbG..."'  # → 'token="***REDACTED***"'
)
```

### InputValidator

Valida inputs contra ataques:
- Shell injection
- Path traversal
- XSS

```python
from backend.buenobot.security import get_validator

validator = get_validator()

# Validar path seguro
is_safe = validator.is_safe_path("../../../etc/passwd", "/app")  # → False

# Validar input
is_safe = validator.is_safe_input("normal_value")  # → True
is_safe = validator.is_safe_input("; rm -rf /")    # → False
```

### AuditLogger

Logging estructurado para auditoría:

```python
from backend.buenobot.security import get_audit_logger

audit = get_audit_logger()

audit.log_scan_start("abc123", "full", "prod", "user@company.com")
audit.log_security_finding("sql_injection", "HIGH", "router.py:45", "...")
audit.log_access_denied("cancel_scan", "unknown_user", "sin permisos")
```

---

## 5. SecureCommandRunner v2.0

### Mejoras

| Feature | v1.0 | v2.0 |
|---------|------|------|
| Timeouts | Individual | Global + individual + multiplicador |
| Cancelación | Kill simple | Graceful terminate → kill |
| Sanitización | Básica | Completa con patrones |
| Logging | Comando completo | Sanitizado |
| Context | - | ExecutionContext con tracking |

### Configuración Global

```python
from backend.buenobot.command_runner import config

# Ajustar timeouts globalmente
config.GLOBAL_TIMEOUT_MULTIPLIER = 1.5  # +50% a todos los timeouts
config.MAX_TIMEOUT = 300  # Máximo 5 minutos

# Habilitar logging completo (solo dev)
config.LOG_FULL_COMMANDS = True

# Límites de output
config.MAX_OUTPUT_SIZE = 200_000  # 200KB
```

### Cancelación Limpia

```python
runner = SecureCommandRunner()

# Cancelar comando específico
await runner.cancel_command(context_id)

# Cancelar todos
cancelled = await runner.cancel_all()
```

---

## 6. Modelo EnhancedFinding v2.0

### Características

```python
class EnhancedFinding(BaseModel):
    id: str                      # UUID único
    title: str
    description: str
    severity: CheckSeverity
    
    # Ubicación detallada
    location: str
    file_path: str
    line_number: int
    column: int
    
    # Múltiples evidencias
    evidences: List[Evidence]    # 🆕 Lista de evidencias
    
    # Recomendación
    recommendation: str
    fix_example: str             # 🆕 Ejemplo de fix
    documentation_url: str       # 🆕 Link a documentación
    
    # Categorización
    priority: str                # P0-P4
    tags: List[str]
    rule_id: str
    
    # Trazabilidad
    related_findings: List[str]  # 🆕 IDs relacionados
    fix_commit: str              # 🆕 SHA del fix
    
    # Métricas
    occurrences: int             # 🆕 Veces encontrado
    first_seen: datetime
    last_seen: datetime
    
    # Estado
    status: str                  # open, fixing, fixed, wont_fix
    assigned_to: str
```

---

## 7. Maturity Assessment

### Evaluación Actual: 7.5/10

| Dimensión | Score | Notas |
|-----------|-------|-------|
| **Cobertura de Checks** | 8/10 | 18 checks en 7 categorías |
| **Seguridad** | 8/10 | Whitelist, sanitización, hardening |
| **Extensibilidad** | 9/10 | Plugin architecture, YAML contracts |
| **Reporting** | 7/10 | JSON + Markdown, falta dashboard histórico |
| **CI/CD Integration** | 6/10 | API REST lista, falta GitHub Actions |
| **Documentación** | 7/10 | Docs completos, faltan ejemplos avanzados |
| **Testing** | 6/10 | Checks testeados, falta test suite completa |
| **Observabilidad** | 8/10 | AuditLogger, progreso en tiempo real |

### Roadmap para 10/10

1. **GitHub Actions Integration** - Trigger automático en PRs
2. **Dashboard Histórico** - Tendencias, métricas en el tiempo
3. **Slack/Teams Notifications** - Alertas en tiempo real
4. **Auto-fix Suggestions** - PRs automáticos para fixes simples
5. **Test Suite Completa** - 90%+ coverage del sistema
6. **Benchmark Database** - Comparar con runs anteriores

### Preparación SaaS

| Requisito SaaS | Estado |
|----------------|--------|
| Multi-tenant | Parcial (separación por scan_id) |
| API REST completa | ✅ |
| Rate limiting | ❌ Pendiente |
| Billing integration | ❌ Pendiente |
| Self-service onboarding | ❌ Pendiente |
| White-labeling | ❌ Pendiente |

---

## Uso Rápido

### Ejecutar Scan Completo

```python
from backend.buenobot.runner import ScanRunner
from backend.buenobot.models import ScanType

runner = ScanRunner(working_dir="/app")
report = await runner.run_scan(
    scan_type=ScanType.FULL,
    environment="prod",
    triggered_by="ci@company.com"
)

print(f"Gate: {report.gate_status}")
print(f"Findings: {len(report.top_findings)}")
```

### Validar Contrato Específico

```python
from backend.buenobot.contracts import ContractValidator, get_contract_registry

registry = get_contract_registry()
contract = registry.get_contract("/api/v1/stock/camaras")

validator = ContractValidator(base_url="http://localhost:8080")
result = await validator.validate_endpoint(contract)

if not result.passed:
    for v in result.violations:
        print(f"  - {v.message}")
```

### Analizar Archivo con AST

```python
from backend.buenobot.checks.backend_design import BackendDesignAnalyzer

analyzer = BackendDesignAnalyzer(working_dir="/app")
issues = analyzer.analyze_file("backend/routers/stock.py")

for issue in issues:
    print(f"[{issue.severity}] {issue.rule}: {issue.message}")
```

---

## Endpoints API

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/v1/buenobot/scan` | Iniciar nuevo scan |
| GET | `/api/v1/buenobot/scan/{id}` | Obtener reporte completo |
| GET | `/api/v1/buenobot/scan/{id}/status` | Estado y progreso |
| GET | `/api/v1/buenobot/scan/{id}/logs` | Logs en tiempo real |
| GET | `/api/v1/buenobot/scans` | Historial de scans |
| POST | `/api/v1/buenobot/scan/{id}/cancel` | Cancelar scan |
| GET | `/api/v1/buenobot/checks` | Lista de checks disponibles |
| GET | `/api/v1/buenobot/compare` | Comparar dos scans |
| GET | `/api/v1/buenobot/health` | Health del sistema |

---

## Changelog v2.0

### New Features
- Output Contract Testing con YAML
- Backend Design Analyzer con AST
- Filter Validation dinámico
- Gate Policy v2 con gate-breakers
- SecuritySanitizer y InputValidator
- AuditLogger estructurado
- EnhancedFinding con evidencias múltiples

### Improvements
- SecureCommandRunner con cancelación limpia
- Timeouts configurables globalmente
- Sanitización de outputs mejorada
- Checklist Go/No-Go automático

### Breaking Changes
- `__version__` cambió de "1.0.0" a "2.0.0"
- Nuevos campos en ScanReport (`checklist`)
- Gate Policy más estricto (puede fallar donde antes pasaba)

---

## Soporte

**Desarrollado por:** Rio Futuro Engineering Team  
**Versión:** 2.0.0  
**Licencia:** Propietaria
