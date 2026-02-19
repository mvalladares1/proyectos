"""
BUENOBOT - Modelos de datos

Define todas las estructuras de datos para el sistema de QA/AppSec.
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import uuid


class ScanType(str, Enum):
    """Tipos de escaneo disponibles"""
    QUICK = "quick"      # Health + lint + deps + secrets + permisos básicos
    FULL = "full"        # Todo lo anterior + tests + performance + infra


class ScanStatus(str, Enum):
    """Estados del escaneo"""
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CheckSeverity(str, Enum):
    """Severidad de hallazgos"""
    CRITICAL = "critical"  # Bloquea deploy
    HIGH = "high"          # Bloquea deploy
    MEDIUM = "medium"      # Warning
    LOW = "low"            # Info
    INFO = "info"          # Informativo


class GateStatus(str, Enum):
    """Estado del gate de release"""
    PASS = "pass"    # Todo OK, puede deployar
    WARN = "warn"    # Warnings pero puede deployar
    FAIL = "fail"    # No debe deployar


class CheckCategory(str, Enum):
    """Categorías de checks"""
    CODE_QUALITY = "code_quality"
    API_QA = "api_qa"
    SECURITY = "security"
    PERMISSIONS = "permissions"
    ODOO_INTEGRITY = "odoo_integrity"
    INFRA = "infra"
    PERFORMANCE = "performance"


class Finding(BaseModel):
    """Un hallazgo individual dentro de un check"""
    title: str
    description: str
    severity: CheckSeverity
    location: Optional[str] = None  # archivo:linea o endpoint
    evidence: Optional[str] = None  # output/snippet
    recommendation: Optional[str] = None
    priority: Optional[str] = None  # P0, P1, P2


class CheckResult(BaseModel):
    """Resultado de un check individual"""
    check_id: str
    check_name: str
    category: CheckCategory
    status: str  # passed, failed, skipped, error
    duration_ms: int = 0
    findings: List[Finding] = []
    summary: str = ""
    raw_output: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def has_critical(self) -> bool:
        return any(f.severity in [CheckSeverity.CRITICAL, CheckSeverity.HIGH] for f in self.findings)
    
    @property
    def has_warnings(self) -> bool:
        return any(f.severity == CheckSeverity.MEDIUM for f in self.findings)


class ScanRequest(BaseModel):
    """Request para iniciar un scan"""
    environment: str = Field(default="dev", description="Entorno: dev o prod")
    scan_type: ScanType = Field(default=ScanType.QUICK)
    checks: Optional[List[str]] = None  # None = todos los checks del tipo
    triggered_by: Optional[str] = None  # Usuario que inició el scan


class ScanResponse(BaseModel):
    """Respuesta al crear un scan"""
    scan_id: str
    status: ScanStatus
    message: str
    created_at: datetime


class GitInfo(BaseModel):
    """Información del repositorio Git"""
    commit_sha: str
    branch: str
    commit_message: Optional[str] = None
    author: Optional[str] = None
    commit_date: Optional[datetime] = None


class ScanMetadata(BaseModel):
    """Metadatos del scan"""
    scan_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    scan_type: ScanType
    environment: str
    triggered_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    git_info: Optional[GitInfo] = None


class ScanProgress(BaseModel):
    """Progreso actual del scan"""
    total_checks: int
    completed_checks: int
    current_check: Optional[str] = None
    percentage: float = 0.0
    logs: List[str] = []


class ScanReport(BaseModel):
    """Reporte completo de un scan"""
    metadata: ScanMetadata
    status: ScanStatus
    gate_status: GateStatus = GateStatus.PASS
    gate_reason: str = ""
    
    # Resultados por categoría
    results: Dict[str, List[CheckResult]] = {}
    
    # Resumen ejecutivo
    summary: Dict[str, Any] = {}
    top_findings: List[Finding] = []
    
    # Checklist Go/No-Go
    checklist: Dict[str, bool] = {}
    
    # Recomendaciones
    recommendations: List[Dict[str, Any]] = []
    
    # Progress (mientras corre)
    progress: Optional[ScanProgress] = None
    
    # Stats
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    warning_checks: int = 0
    duration_seconds: float = 0.0
    
    def compute_gate_status(self) -> None:
        """
        Calcula el estado del gate basado en los resultados.
        
        Gate Policy v2.0:
        - FAIL inmediato si:
          * Credenciales en query params
          * Credenciales expuestas en output
          * Filtros no respetados (data leak)
          * Datos fuera de rango crítico
          * Vulnerabilidades de seguridad HIGH/CRITICAL
        
        - WARN si:
          * Advertencias de código
          * Issues de rendimiento
          * Datos fuera de rango menor
        """
        critical_findings = []
        high_findings = []
        warning_findings = []
        
        # Gate-breakers inmediatos (reglas que causan FAIL automático)
        gate_breaker_rules = {
            "password_in_query_params",
            "no_credentials_in_output", 
            "hardcoded_credentials",
            "respects_filter",  # Data leak por filtro no aplicado
            "sql_injection_risk",
        }
        
        gate_breakers_found = []
        
        for category_results in self.results.values():
            for check in category_results:
                for finding in check.findings:
                    # Detectar gate-breakers por título de finding
                    rule_name = self._extract_rule_name(finding.title)
                    
                    if rule_name in gate_breaker_rules:
                        gate_breakers_found.append(finding)
                    elif finding.severity == CheckSeverity.CRITICAL:
                        critical_findings.append(finding)
                    elif finding.severity == CheckSeverity.HIGH:
                        high_findings.append(finding)
                    elif finding.severity == CheckSeverity.MEDIUM:
                        warning_findings.append(finding)
        
        # Evaluar Gate Status
        if gate_breakers_found:
            self.gate_status = GateStatus.FAIL
            self.gate_reason = self._format_gate_reason(gate_breakers_found, "CRÍTICO")
        elif critical_findings:
            self.gate_status = GateStatus.FAIL
            self.gate_reason = f"{len(critical_findings)} hallazgos CRÍTICOS bloquean deploy"
        elif high_findings:
            self.gate_status = GateStatus.FAIL
            self.gate_reason = f"{len(high_findings)} hallazgos HIGH requieren atención antes de deploy"
        elif warning_findings:
            self.gate_status = GateStatus.WARN
            self.gate_reason = f"{len(warning_findings)} advertencias - deploy posible con precaución"
        else:
            self.gate_status = GateStatus.PASS
            self.gate_reason = "✓ Todos los checks pasaron - listo para deploy"
        
        # Top findings ordenados por prioridad
        all_important = gate_breakers_found + critical_findings + high_findings + warning_findings
        self.top_findings = all_important[:5]
        
        # Generar checklist Go/No-Go
        self.checklist = self._generate_checklist()
    
    def _extract_rule_name(self, title: str) -> str:
        """Extrae nombre de regla del título del finding"""
        # Formato esperado: "[rule_name] mensaje" 
        if title.startswith("[") and "]" in title:
            return title[1:title.index("]")]
        return ""
    
    def _format_gate_reason(self, findings: List[Finding], level: str) -> str:
        """Formatea razón del gate con detalles"""
        unique_rules = set(self._extract_rule_name(f.title) for f in findings)
        rules_str = ", ".join(r for r in unique_rules if r) or "múltiples issues"
        return f"{level}: {len(findings)} hallazgos de seguridad ({rules_str}) bloquean deploy"
    
    def _generate_checklist(self) -> Dict[str, bool]:
        """Genera checklist Go/No-Go basado en resultados"""
        checks = {
            "sin_credenciales_expuestas": True,
            "sin_vulnerabilidades_criticas": True,
            "filtros_funcionando": True,
            "codigo_sin_errores_criticos": True,
            "api_respondiendo": True,
            "permisos_correctos": True,
        }
        
        # Analizar resultados para marcar checklist
        for category, results in self.results.items():
            for check in results:
                if check.status == "failed":
                    # Marcar items relevantes como fallidos
                    if "credential" in check.check_id.lower() or "secret" in check.check_id.lower():
                        checks["sin_credenciales_expuestas"] = False
                    if "security" in category.lower():
                        checks["sin_vulnerabilidades_criticas"] = False
                    if "filter" in check.check_id.lower() or "contract" in check.check_id.lower():
                        checks["filtros_funcionando"] = False
                    if "permission" in check.check_id.lower():
                        checks["permisos_correctos"] = False
                    if "health" in check.check_id.lower() or "smoke" in check.check_id.lower():
                        checks["api_respondiendo"] = False
        
        return checks


class ScanListItem(BaseModel):
    """Item para listado de scans (versión resumida)"""
    scan_id: str
    scan_type: ScanType
    environment: str
    status: ScanStatus
    gate_status: GateStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    commit_sha: Optional[str] = None
    triggered_by: Optional[str] = None
    summary: str = ""


# === MODELOS v2.0 ADICIONALES ===

class Evidence(BaseModel):
    """
    Evidencia detallada de un hallazgo v2.0
    
    Proporciona contexto rico para debugging y auditoría.
    """
    evidence_type: str = "text"  # text, code, json, url, screenshot
    content: str
    source: Optional[str] = None  # archivo:linea, endpoint, etc.
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = {}


class EnhancedFinding(BaseModel):
    """
    Finding v2.0 con evidencia estructurada y trazabilidad.
    
    Mejoras sobre Finding v1.0:
    - Múltiples evidencias
    - Trazabilidad (related_findings, fix_commit)
    - Métricas (occurrences, first_seen)
    - Estado de remediación
    """
    id: str = ""  # UUID del finding
    title: str
    description: str
    severity: CheckSeverity
    
    # Ubicación detallada
    location: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    column: Optional[int] = None
    
    # Evidencias múltiples
    evidences: List[Evidence] = []
    
    # Recomendación y fix
    recommendation: Optional[str] = None
    fix_example: Optional[str] = None
    documentation_url: Optional[str] = None
    
    # Prioridad y categorización
    priority: Optional[str] = None  # P0-P4
    tags: List[str] = []
    rule_id: Optional[str] = None
    
    # Trazabilidad
    related_findings: List[str] = []  # IDs de findings relacionados
    fix_commit: Optional[str] = None  # SHA del commit que lo arregló
    
    # Métricas
    occurrences: int = 1
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    
    # Estado
    status: str = "open"  # open, acknowledged, fixing, fixed, wont_fix
    assigned_to: Optional[str] = None
    
    def to_simple_finding(self) -> Finding:
        """Convierte a Finding simple para compatibilidad"""
        return Finding(
            title=self.title,
            description=self.description,
            severity=self.severity,
            location=self.location,
            evidence=self.evidences[0].content if self.evidences else None,
            recommendation=self.recommendation,
            priority=self.priority
        )
    
    @classmethod
    def from_simple_finding(cls, finding: Finding, rule_id: str = "") -> "EnhancedFinding":
        """Crea EnhancedFinding desde Finding simple"""
        import uuid
        evidences = []
        if finding.evidence:
            evidences.append(Evidence(
                evidence_type="text",
                content=finding.evidence,
                source=finding.location
            ))
        
        return cls(
            id=str(uuid.uuid4())[:8],
            title=finding.title,
            description=finding.description,
            severity=finding.severity,
            location=finding.location,
            evidences=evidences,
            recommendation=finding.recommendation,
            priority=finding.priority,
            rule_id=rule_id,
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow()
        )


# === MODELOS v3.0 - AI ANALYSIS ===

class AIRootCause(BaseModel):
    """Root cause identificado por IA"""
    cause: str
    evidence_ids: List[str] = []
    severity: str = "medium"
    explanation: str = ""


class AIRecommendation(BaseModel):
    """Recomendación generada por IA"""
    title: str
    priority: str = "P2"  # P0-P4
    effort: str = "medium"  # low, medium, high
    description: str = ""
    code_example: Optional[str] = None


class AIAnalysisResult(BaseModel):
    """
    Resultado del análisis de IA v3.0
    
    Generado por el AI Gateway (local o OpenAI).
    Complementa el análisis determinístico.
    """
    # Estado
    enabled: bool = False
    engine_used: Optional[str] = None  # "local", "openai", "mock"
    engine_reason: Optional[str] = None
    
    # Tiempos
    analysis_ms: int = 0
    cached: bool = False
    
    # Resultados
    summary: Optional[str] = None
    root_causes: List[AIRootCause] = []
    recommendations: List[AIRecommendation] = []
    
    # Métricas
    risk_score: int = 0  # 0-100
    confidence: float = 0.0  # 0.0-1.0
    
    # Insights adicionales
    suggested_next_checks: List[str] = []
    notable_anomalies: List[str] = []
    
    # Error handling
    error: Optional[str] = None
    skipped_reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa a diccionario"""
        return {
            "enabled": self.enabled,
            "engine_used": self.engine_used,
            "engine_reason": self.engine_reason,
            "analysis_ms": self.analysis_ms,
            "cached": self.cached,
            "summary": self.summary,
            "root_causes": [rc.dict() for rc in self.root_causes],
            "recommendations": [rec.dict() for rec in self.recommendations],
            "risk_score": self.risk_score,
            "confidence": self.confidence,
            "suggested_next_checks": self.suggested_next_checks,
            "notable_anomalies": self.notable_anomalies,
            "error": self.error,
            "skipped_reason": self.skipped_reason
        }
    
    @classmethod
    def from_gateway_response(cls, response: Dict[str, Any]) -> "AIAnalysisResult":
        """Crea instancia desde respuesta del AIGateway"""
        if response.get("skipped"):
            return cls(
                enabled=False,
                skipped_reason=response.get("reason", "Unknown")
            )
        
        if response.get("error"):
            return cls(
                enabled=True,
                engine_used=response.get("engine_used"),
                error=str(response.get("error"))
            )
        
        # Parsear root causes
        root_causes = []
        for rc in response.get("root_causes", []):
            root_causes.append(AIRootCause(
                cause=rc.get("cause", ""),
                evidence_ids=rc.get("evidence_ids", []),
                severity=rc.get("severity", "medium"),
                explanation=rc.get("explanation", "")
            ))
        
        # Parsear recommendations
        recommendations = []
        for rec in response.get("recommendations", []):
            recommendations.append(AIRecommendation(
                title=rec.get("title", ""),
                priority=rec.get("priority", "P2"),
                effort=rec.get("effort", "medium"),
                description=rec.get("description", ""),
                code_example=rec.get("code_example")
            ))
        
        return cls(
            enabled=True,
            engine_used=response.get("engine_used"),
            engine_reason=response.get("engine_reason"),
            analysis_ms=response.get("analysis_ms", 0),
            cached=response.get("cached", False),
            summary=response.get("summary"),
            root_causes=root_causes,
            recommendations=recommendations,
            risk_score=response.get("risk_score", 0),
            confidence=response.get("confidence", 0.0),
            suggested_next_checks=response.get("suggested_next_checks", []),
            notable_anomalies=response.get("notable_anomalies", [])
        )


class ScanReportV3(ScanReport):
    """
    Reporte de scan v3.0 con análisis de IA.
    
    Extiende ScanReport con campos de IA.
    """
    # AI Analysis
    ai_analysis: Optional[AIAnalysisResult] = None
    
    # Evidence hash para cache
    evidence_hash: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa el reporte completo"""
        base = {
            "metadata": self.metadata.dict() if self.metadata else {},
            "status": self.status.value if self.status else "unknown",
            "gate_status": self.gate_status.value if self.gate_status else "unknown",
            "gate_reason": self.gate_reason,
            "results": {k: [r.dict() for r in v] for k, v in self.results.items()},
            "summary": self.summary,
            "top_findings": [f.dict() for f in self.top_findings],
            "checklist": self.checklist,
            "recommendations": self.recommendations,
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "warning_checks": self.warning_checks,
            "duration_seconds": self.duration_seconds
        }
        
        # Añadir AI
        if self.ai_analysis:
            base["ai_analysis"] = self.ai_analysis.to_dict()
        
        if self.evidence_hash:
            base["evidence_hash"] = self.evidence_hash
        
        return base

