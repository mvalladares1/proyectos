"""
BUENOBOT v2.0 - Checks Package

Cada check es un plugin que implementa la interfaz BaseCheck.
Los checks están organizados por categoría.

v2.0 nuevos checks:
- OutputContractCheck: Validación de contratos YAML
- FilterValidationCheck: Validación de filtros dinámicos  
- BackendDesignCheck: Análisis AST de código
"""

from .base import BaseCheck, CheckRegistry
from .code_quality import RuffLintCheck, MypyCheck
from .security import PipAuditCheck, BanditCheck, SecretsCheck
from .api_qa import HealthCheck, EndpointSmokeCheck, AuthCheck
from .permissions import PermissionsCheck
from .odoo_integrity import OdooConnectivityCheck
from .infra import DockerStatusCheck, LogsCheck, ResourcesCheck
from .performance import EndpointPerformanceCheck

# v2.0 checks
from .output_qa import OutputContractCheck, FilterValidationCheck
from .backend_design import BackendDesignCheck

__all__ = [
    'BaseCheck',
    'CheckRegistry',
    # Code Quality
    'RuffLintCheck',
    'MypyCheck',
    'BackendDesignCheck',  # v2.0
    # Security
    'PipAuditCheck',
    'BanditCheck',
    'SecretsCheck',
    # API QA
    'HealthCheck',
    'EndpointSmokeCheck',
    'AuthCheck',
    'OutputContractCheck',  # v2.0
    'FilterValidationCheck',  # v2.0
    # Permissions
    'PermissionsCheck',
    # Odoo
    'OdooConnectivityCheck',
    # Infra
    'DockerStatusCheck',
    'LogsCheck',
    'ResourcesCheck',
    # Performance
    'EndpointPerformanceCheck',
]
