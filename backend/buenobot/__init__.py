"""
BUENOBOT v2.0 - Motor Inteligente de Validación Backend-Aware

Sistema de QA y Seguridad para Rio Futuro Dashboards.
Ejecuta revisiones automatizadas antes de lanzar a producción.

Nuevas características v2.0:
- Output Contract Testing: Validación YAML de respuestas API
- Backend Design Analysis: Análisis AST de código
- Filter Validation: Verificación dinámica de filtros
- Gate Policy v2: Reglas estrictas de seguridad
- Security Hardening: Sanitización de logs y outputs

Arquitectura:
- models.py: Modelos Pydantic para scans, checks, reportes
- storage.py: Persistencia de historial de scans (JSON/disk)
- runner.py: Orquestador de jobs asíncronos
- command_runner.py: Ejecución segura con whitelist v2
- security.py: Hardening y sanitización
- contracts/: Sistema de contratos YAML para outputs
- checks/: Plugins de verificación por categoría (18 checks)
"""

__version__ = "2.0.0"
__author__ = "Rio Futuro Engineering Team"

from .models import (
    ScanType,
    ScanStatus,
    CheckSeverity,
    GateStatus,
    CheckResult,
    ScanRequest,
    ScanResponse,
    ScanReport,
    Evidence,
    EnhancedFinding,
)

__all__ = [
    'ScanType',
    'ScanStatus', 
    'CheckSeverity',
    'GateStatus',
    'CheckResult',
    'ScanRequest',
    'ScanResponse',
    'ScanReport'
]
