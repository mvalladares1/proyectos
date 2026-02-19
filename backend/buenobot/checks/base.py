"""
BUENOBOT - Base Check Class

Clase base para todos los checks del sistema.
Implementa el patrón Plugin con registro automático.
"""
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Type, Any
from datetime import datetime

from ..models import CheckResult, CheckCategory, Finding, CheckSeverity
from ..command_runner import SecureCommandRunner

logger = logging.getLogger(__name__)


class CheckRegistry:
    """
    Registro global de checks disponibles.
    Permite descubrir y ejecutar checks por categoría.
    """
    _checks: Dict[str, Type['BaseCheck']] = {}
    _quick_checks: List[str] = []
    _full_checks: List[str] = []
    
    @classmethod
    def register(
        cls,
        check_id: str,
        quick: bool = True,
        full: bool = True
    ):
        """
        Decorador para registrar un check.
        
        Args:
            check_id: ID único del check
            quick: Incluir en Quick Scan
            full: Incluir en Full Scan
        """
        def decorator(check_class: Type['BaseCheck']):
            cls._checks[check_id] = check_class
            if quick:
                cls._quick_checks.append(check_id)
            if full and check_id not in cls._full_checks:
                cls._full_checks.append(check_id)
            return check_class
        return decorator
    
    @classmethod
    def get_check(cls, check_id: str) -> Optional[Type['BaseCheck']]:
        """Obtiene una clase de check por ID"""
        return cls._checks.get(check_id)
    
    @classmethod
    def get_quick_checks(cls) -> List[str]:
        """Lista checks para Quick Scan"""
        return cls._quick_checks.copy()
    
    @classmethod
    def get_full_checks(cls) -> List[str]:
        """Lista checks para Full Scan"""
        # Full incluye todos los quick + adicionales
        return list(set(cls._quick_checks + cls._full_checks))
    
    @classmethod
    def get_all_checks(cls) -> Dict[str, Type['BaseCheck']]:
        """Obtiene todos los checks registrados"""
        return cls._checks.copy()
    
    @classmethod
    def list_checks(cls) -> List[Dict[str, Any]]:
        """Lista información de todos los checks"""
        result = []
        for check_id, check_class in cls._checks.items():
            result.append({
                "id": check_id,
                "name": check_class.name,
                "category": check_class.category.value,
                "description": check_class.description,
                "in_quick": check_id in cls._quick_checks,
                "in_full": check_id in cls._full_checks
            })
        return result


class BaseCheck(ABC):
    """
    Clase base abstracta para todos los checks.
    
    Cada check debe implementar:
    - name: Nombre del check
    - category: Categoría (CheckCategory)
    - description: Descripción breve
    - run(): Método principal que ejecuta el check
    """
    
    name: str = "Base Check"
    category: CheckCategory = CheckCategory.CODE_QUALITY
    description: str = "Check base"
    
    def __init__(
        self,
        working_dir: str = "/app",
        environment: str = "dev",
        api_base_url: Optional[str] = None
    ):
        self.working_dir = working_dir
        self.environment = environment
        self.api_base_url = api_base_url or self._get_api_url()
        self.command_runner = SecureCommandRunner(working_dir)
        self.findings: List[Finding] = []
        self.logs: List[str] = []
    
    def _get_api_url(self) -> str:
        """Determina la URL del API según el entorno"""
        import os
        if self.environment == "prod":
            return os.environ.get("API_URL_PROD", "http://localhost:8001")
        return os.environ.get("API_URL_DEV", "http://localhost:8002")
    
    def log(self, message: str, level: str = "info"):
        """Agrega un mensaje al log del check"""
        timestamp = datetime.utcnow().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{level.upper()}] {self.name}: {message}"
        self.logs.append(log_entry)
        
        if level == "error":
            logger.error(log_entry)
        elif level == "warning":
            logger.warning(log_entry)
        else:
            logger.info(log_entry)
    
    def add_finding(
        self,
        title: str,
        description: str,
        severity: CheckSeverity,
        location: Optional[str] = None,
        evidence: Optional[str] = None,
        recommendation: Optional[str] = None,
        priority: Optional[str] = None
    ):
        """Agrega un hallazgo al check"""
        # Auto-asignar prioridad si no se especifica
        if priority is None:
            priority = {
                CheckSeverity.CRITICAL: "P0",
                CheckSeverity.HIGH: "P0",
                CheckSeverity.MEDIUM: "P1",
                CheckSeverity.LOW: "P2",
                CheckSeverity.INFO: "P2"
            }.get(severity, "P2")
        
        finding = Finding(
            title=title,
            description=description,
            severity=severity,
            location=location,
            evidence=evidence,
            recommendation=recommendation,
            priority=priority
        )
        self.findings.append(finding)
        self.log(f"Finding [{severity.value}]: {title}", "warning")
    
    @abstractmethod
    async def run(self) -> CheckResult:
        """
        Ejecuta el check y retorna el resultado.
        
        Debe ser implementado por cada check concreto.
        """
        pass
    
    async def execute(self) -> CheckResult:
        """
        Wrapper que ejecuta el check con timing y manejo de errores.
        """
        start_time = time.time()
        self.findings = []
        self.logs = []
        
        self.log(f"Iniciando check...")
        
        try:
            result = await self.run()
            result.duration_ms = int((time.time() - start_time) * 1000)
            result.findings = self.findings
            result.raw_output = "\n".join(self.logs[-50:])  # Últimos 50 logs
            
            self.log(f"Check completado: {result.status}")
            return result
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.log(f"Error en check: {str(e)}", "error")
            
            return CheckResult(
                check_id=self.__class__.__name__.lower(),
                check_name=self.name,
                category=self.category,
                status="error",
                duration_ms=duration_ms,
                findings=self.findings,
                summary=f"Error: {str(e)}",
                raw_output="\n".join(self.logs)
            )
    
    def _create_result(
        self,
        status: str,
        summary: str = ""
    ) -> CheckResult:
        """Helper para crear un CheckResult"""
        return CheckResult(
            check_id=self.__class__.__name__.lower(),
            check_name=self.name,
            category=self.category,
            status=status,
            summary=summary,
            findings=self.findings
        )
