"""
BUENOBOT v3.0 - EvidencePack Builder

Construye paquetes de evidencia sanitizados para enviar a la IA.
Maneja límites de tokens, sanitización y estructuración.
"""
import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional

from .config import get_ai_config
from .security import get_sanitizer

logger = logging.getLogger(__name__)


@dataclass
class EvidencePack:
    """
    Paquete de evidencia para análisis IA.
    
    Contiene todos los datos del scan en formato
    seguro y limitado para envío a LLMs.
    """
    # Identificadores
    scan_id: str
    scan_type: str = "full"
    environment: str = "unknown"
    commit_sha: Optional[str] = None
    
    # Estado del gate (determinístico)
    gate_status: str = "unknown"  # PASS, WARN, FAIL
    gate_reasons: List[str] = field(default_factory=list)
    
    # Checklist de verificaciones
    checklist: Dict[str, bool] = field(default_factory=dict)
    
    # Risk triggers detectados
    risk_triggers: List[str] = field(default_factory=list)
    
    # Top findings (limitados)
    top_findings: List[Dict[str, Any]] = field(default_factory=list)
    
    # Violaciones de contratos
    contract_violations: List[Dict[str, Any]] = field(default_factory=list)
    
    # Issues de diseño backend (AST)
    backend_ast_issues: List[Dict[str, Any]] = field(default_factory=list)
    
    # Métricas de performance/stats
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def compute_hash(self) -> str:
        """Computa hash del contenido para cache"""
        content = (
            f"{self.scan_id}:{self.environment}:{self.gate_status}:"
            f"{','.join(sorted(self.risk_triggers))}:"
            f"{len(self.top_findings)}:{len(self.contract_violations)}"
        )
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario serializable"""
        return {
            "scan_id": self.scan_id,
            "scan_type": self.scan_type,
            "environment": self.environment,
            "commit_sha": self.commit_sha,
            "gate_status": self.gate_status,
            "gate_reasons": self.gate_reasons,
            "checklist": self.checklist,
            "risk_triggers": self.risk_triggers,
            "top_findings": self.top_findings,
            "contract_violations": self.contract_violations,
            "backend_ast_issues": self.backend_ast_issues,
            "performance_metrics": self.performance_metrics,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidencePack":
        """Crea instancia desde diccionario"""
        return cls(
            scan_id=data.get("scan_id", "unknown"),
            scan_type=data.get("scan_type", "full"),
            environment=data.get("environment", "unknown"),
            commit_sha=data.get("commit_sha"),
            gate_status=data.get("gate_status", "unknown"),
            gate_reasons=data.get("gate_reasons", []),
            checklist=data.get("checklist", {}),
            risk_triggers=data.get("risk_triggers", []),
            top_findings=data.get("top_findings", []),
            contract_violations=data.get("contract_violations", []),
            backend_ast_issues=data.get("backend_ast_issues", []),
            performance_metrics=data.get("performance_metrics", {}),
            created_at=data.get("created_at", datetime.utcnow().isoformat())
        )


class EvidencePackBuilder:
    """
    Constructor de EvidencePack desde ScanReport.
    
    Maneja:
    - Sanitización de datos sensibles
    - Límite de findings
    - Priorización por severidad
    - Extracción de métricas
    """
    
    # Patrones de datos sensibles a sanitizar
    SENSITIVE_PATTERNS = [
        (r'password[=:]\s*["\']?[\w@#$%^&*]+["\']?', 'password=***'),
        (r'api[_-]?key[=:]\s*["\']?[\w-]+["\']?', 'api_key=***'),
        (r'secret[=:]\s*["\']?[\w-]+["\']?', 'secret=***'),
        (r'token[=:]\s*["\']?[\w.-]+["\']?', 'token=***'),
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '***@***.***'),
        (r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', '***.***.***.***'),
    ]
    
    def __init__(self):
        self.config = get_ai_config()
        self.sanitizer = get_sanitizer()
    
    def build(
        self,
        scan_report: "ScanReport",  # Forward reference
        environment: str = "unknown",
        commit_sha: Optional[str] = None
    ) -> EvidencePack:
        """
        Construye EvidencePack desde un ScanReport.
        
        Args:
            scan_report: Resultado del scan
            environment: dev/staging/prod
            commit_sha: Hash del commit (para cache)
        
        Returns:
            EvidencePack sanitizado y limitado
        """
        # Extraer findings ordenados por severidad
        top_findings = self._extract_top_findings(scan_report)
        
        # Extraer risk triggers
        risk_triggers = self._extract_risk_triggers(scan_report)
        
        # Separar contract violations y AST issues
        contract_violations = []
        backend_ast_issues = []
        
        for finding in scan_report.findings:
            if finding.check_name == "OutputContractCheck":
                contract_violations.append(self._sanitize_finding(finding))
            elif finding.check_name == "BackendDesignCheck":
                backend_ast_issues.append(self._sanitize_finding(finding))
        
        # Construir checklist
        checklist = self._build_checklist(scan_report)
        
        # Gate reasons
        gate_reasons = self._extract_gate_reasons(scan_report)
        
        return EvidencePack(
            scan_id=scan_report.scan_id,
            scan_type="full",
            environment=environment,
            commit_sha=commit_sha,
            gate_status=scan_report.gate_status,
            gate_reasons=gate_reasons,
            checklist=checklist,
            risk_triggers=risk_triggers,
            top_findings=top_findings,
            contract_violations=contract_violations[:10],
            backend_ast_issues=backend_ast_issues[:10],
            performance_metrics={
                "total_findings": scan_report.total_findings,
                "findings_by_severity": scan_report.findings_by_severity,
                "scan_duration_ms": getattr(scan_report, 'scan_duration_ms', 0)
            }
        )
    
    def _extract_top_findings(self, scan_report: "ScanReport") -> List[Dict[str, Any]]:
        """Extrae y prioriza los findings más importantes"""
        
        # Ordenar por severidad
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        
        sorted_findings = sorted(
            scan_report.findings,
            key=lambda f: (
                severity_order.get(f.severity.lower(), 5),
                not f.is_gate_breaker
            )
        )
        
        # Limitar cantidad
        max_findings = self.config.max_findings_to_ai
        
        return [
            self._sanitize_finding(f)
            for f in sorted_findings[:max_findings]
        ]
    
    def _sanitize_finding(self, finding: Any) -> Dict[str, Any]:
        """Sanitiza un finding individual"""
        
        # Convertir a dict si es necesario
        if hasattr(finding, 'dict'):
            data = finding.dict()
        elif hasattr(finding, 'to_dict'):
            data = finding.to_dict()
        else:
            data = dict(finding) if isinstance(finding, dict) else {}
        
        # Sanitizar campos de texto
        for key in ['title', 'description', 'evidence', 'location', 'message']:
            if key in data and data[key]:
                data[key] = self._sanitize_text(str(data[key]))
        
        return data
    
    def _sanitize_text(self, text: str) -> str:
        """Sanitiza texto removiendo datos sensibles"""
        result = text
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        return result
    
    def _extract_risk_triggers(self, scan_report: "ScanReport") -> List[str]:
        """Extrae triggers de riesgo del scan"""
        triggers = []
        
        # De los findings
        for finding in scan_report.findings:
            # Gate breakers
            if finding.is_gate_breaker:
                # Extraer el nombre de la regla/check
                if hasattr(finding, 'rule_id') and finding.rule_id:
                    triggers.append(finding.rule_id)
                elif hasattr(finding, 'code') and finding.code:
                    triggers.append(finding.code)
            
            # Patrones específicos conocidos
            title_lower = (finding.title or "").lower()
            if "password" in title_lower and "query" in title_lower:
                triggers.append("password_in_query_params")
            if "print" in title_lower:
                triggers.append("print_in_routers")
            if "sql" in title_lower and "injection" in title_lower:
                triggers.append("sql_injection")
        
        return list(set(triggers))
    
    def _build_checklist(self, scan_report: "ScanReport") -> Dict[str, bool]:
        """Construye checklist de verificaciones"""
        checklist = {}
        
        # Agrupar por check
        checks_run = set()
        checks_passed = set()
        
        for finding in scan_report.findings:
            check_name = finding.check_name
            checks_run.add(check_name)
            
            if finding.severity.lower() in ["info", "low"]:
                checks_passed.add(check_name)
        
        # Construir dict
        for check in checks_run:
            checklist[check] = check in checks_passed
        
        return checklist
    
    def _extract_gate_reasons(self, scan_report: "ScanReport") -> List[str]:
        """Extrae razones del gate decision"""
        reasons = []
        
        for finding in scan_report.findings:
            if finding.is_gate_breaker:
                reason = f"[{finding.severity.upper()}] {finding.title}"
                if reason not in reasons:
                    reasons.append(reason)
        
        return reasons


# Singleton builder
_builder_instance: Optional[EvidencePackBuilder] = None


def get_evidence_builder() -> EvidencePackBuilder:
    """Obtiene instancia singleton del builder"""
    global _builder_instance
    if _builder_instance is None:
        _builder_instance = EvidencePackBuilder()
    return _builder_instance
