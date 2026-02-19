"""
BUENOBOT v3.0 - AI Gateway

Orquestador principal que coordina la generación de reportes enriquecidos con IA.
Implementa cache, routing y fallbacks.
"""
import asyncio
import logging
import hashlib
import json
from datetime import datetime
from typing import Optional, Dict, Any

from ..config import get_ai_config
from ..evidence import EvidencePack
from .router import AIRouter, EngineSelection
from .local_engine import LocalEngine
from .openai_engine import OpenAIEngine
from .anthropic_engine import AnthropicEngine
from ..cache_ai import AICache, get_ai_cache

logger = logging.getLogger(__name__)


class AIEnrichedReport:
    """Reporte enriquecido con análisis IA"""
    
    def __init__(
        self,
        scan_id: str,
        ai_status: str = "pending",  # pending, completed, skipped, failed
        engine_used: Optional[str] = None,
        summary: str = "",
        root_causes: list = None,
        recommendations: list = None,
        risk_score: int = 0,
        confidence: float = 0.0,
        suggested_next_checks: list = None,
        notable_anomalies: list = None,
        processing_time_ms: int = 0,
        error_message: Optional[str] = None,
        cached: bool = False,
        created_at: datetime = None
    ):
        self.scan_id = scan_id
        self.ai_status = ai_status
        self.engine_used = engine_used
        self.summary = summary
        self.root_causes = root_causes or []
        self.recommendations = recommendations or []
        self.risk_score = risk_score
        self.confidence = confidence
        self.suggested_next_checks = suggested_next_checks or []
        self.notable_anomalies = notable_anomalies or []
        self.processing_time_ms = processing_time_ms
        self.error_message = error_message
        self.cached = cached
        self.created_at = created_at or datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scan_id": self.scan_id,
            "ai_status": self.ai_status,
            "engine_used": self.engine_used,
            "summary": self.summary,
            "root_causes": self.root_causes,
            "recommendations": self.recommendations,
            "risk_score": self.risk_score,
            "confidence": self.confidence,
            "suggested_next_checks": self.suggested_next_checks,
            "notable_anomalies": self.notable_anomalies,
            "processing_time_ms": self.processing_time_ms,
            "error_message": self.error_message,
            "cached": self.cached,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def skipped(cls, scan_id: str, reason: str = "AI disabled") -> "AIEnrichedReport":
        """Crea reporte marcado como skipped"""
        return cls(
            scan_id=scan_id,
            ai_status="skipped",
            error_message=reason
        )
    
    @classmethod
    def failed(cls, scan_id: str, error: str) -> "AIEnrichedReport":
        """Crea reporte marcado como failed"""
        return cls(
            scan_id=scan_id,
            ai_status="failed",
            error_message=error
        )


class AIGateway:
    """
    Gateway principal de IA.
    
    Responsabilidades:
    - Determinar qué motor usar (local vs API)
    - Manejar cache de respuestas
    - Ejecutar análisis y parsear resultados
    - Implementar fallbacks
    """
    
    def __init__(self):
        self.config = get_ai_config()
        self.router = AIRouter()
        self.cache = get_ai_cache()
        self.local_engine = LocalEngine()
        self.openai_engine = OpenAIEngine()
        self.anthropic_engine = AnthropicEngine()
    
    def _compute_evidence_hash(self, evidence: EvidencePack) -> str:
        """Genera hash único del EvidencePack para cache"""
        # Usar campos estables para el hash
        hash_input = json.dumps({
            "scan_id": evidence.scan_id,
            "commit_sha": evidence.commit_sha,
            "gate_status": evidence.gate_status,
            "findings_count": len(evidence.top_findings),
            "risk_triggers": sorted(evidence.risk_triggers),
        }, sort_keys=True)
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    async def analyze(
        self,
        evidence: EvidencePack,
        analysis_mode: str = "basic",
        force_engine: Optional[str] = None
    ) -> AIEnrichedReport:
        """
        Analiza EvidencePack y genera reporte enriquecido.
        
        Args:
            evidence: EvidencePack con datos del scan
            analysis_mode: "basic" (local) o "deep" (API)
            force_engine: Forzar motor específico (local, openai, mock)
        
        Returns:
            AIEnrichedReport con análisis
        """
        import time
        start_time = time.time()
        
        # Verificar si IA está habilitada
        if not self.config.ai_enabled:
            logger.info("AI disabled, skipping analysis")
            return AIEnrichedReport.skipped(evidence.scan_id, "AI disabled in config")
        
        # Verificar cache
        if self.config.cache_enabled:
            evidence_hash = self._compute_evidence_hash(evidence)
            cache_key = f"{evidence.commit_sha}_{evidence_hash}"
            
            cached_result = await self.cache.get(cache_key)
            if cached_result:
                logger.info(f"AI cache hit for {cache_key}")
                cached_result["cached"] = True
                return self._dict_to_report(evidence.scan_id, cached_result)
        
        # Determinar motor
        if force_engine:
            engine_selection = EngineSelection(
                engine=force_engine,
                reason=f"Forced: {force_engine}"
            )
        else:
            engine_selection = self.router.select_engine(evidence, analysis_mode)
        
        logger.info(f"Selected engine: {engine_selection.engine} ({engine_selection.reason})")
        
        # Ejecutar análisis
        try:
            if engine_selection.engine == "openai":
                result = await self._run_openai(evidence)
            elif engine_selection.engine == "anthropic":
                result = await self._run_anthropic(evidence)
            elif engine_selection.engine == "local":
                result = await self._run_local(evidence)
            else:  # mock
                result = await self._run_mock(evidence)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            # Guardar en cache
            if self.config.cache_enabled and result.ai_status == "completed":
                await self.cache.set(cache_key, result.to_dict())
            
            result.processing_time_ms = processing_time
            return result
            
        except Exception as e:
            logger.exception(f"AI analysis failed: {e}")
            
            # Intentar fallback a local si falló API engine
            if engine_selection.engine in ("openai", "anthropic"):
                logger.info("Falling back to local engine")
                try:
                    result = await self._run_local(evidence)
                    result.engine_used = "local (fallback)"
                    return result
                except Exception as e2:
                    logger.exception(f"Local fallback also failed: {e2}")
            
            return AIEnrichedReport.failed(evidence.scan_id, str(e))
    
    async def _run_openai(self, evidence: EvidencePack) -> AIEnrichedReport:
        """Ejecuta análisis con OpenAI"""
        response = await self.openai_engine.generate(evidence)
        return self._parse_ai_response(evidence.scan_id, response, "openai")
    
    async def _run_anthropic(self, evidence: EvidencePack) -> AIEnrichedReport:
        """Ejecuta análisis con Anthropic Claude"""
        response = await self.anthropic_engine.generate(evidence)
        return self._parse_ai_response(evidence.scan_id, response, "anthropic")
    
    async def _run_local(self, evidence: EvidencePack) -> AIEnrichedReport:
        """Ejecuta análisis con motor local"""
        response = await self.local_engine.generate(evidence)
        return self._parse_ai_response(evidence.scan_id, response, "local")
    
    async def _run_mock(self, evidence: EvidencePack) -> AIEnrichedReport:
        """Genera respuesta mock para desarrollo"""
        # Simular delay
        await asyncio.sleep(0.5)
        
        # Generar respuesta basada en evidence
        has_critical = any(f.get("severity") in ["critical", "high"] for f in evidence.top_findings)
        
        mock_summary = f"Scan {evidence.scan_id} analyzed. "
        if has_critical:
            mock_summary += f"Found {len(evidence.top_findings)} issues requiring attention. "
            if "password_in_query_params" in evidence.risk_triggers:
                mock_summary += "CRITICAL: Credentials exposed in query parameters detected. "
        else:
            mock_summary += "No critical issues found. "
        
        mock_causes = []
        if "password_in_query_params" in evidence.risk_triggers:
            mock_causes.append({
                "cause": "Security credentials in URL query parameters",
                "evidence_ids": ["backend_design_finding_1"],
                "severity": "critical",
                "explanation": "Passwords in query params are logged in server access logs, browser history, and can leak via referer headers."
            })
        
        mock_recommendations = []
        if "password_in_query_params" in evidence.risk_triggers:
            mock_recommendations.append({
                "title": "Move credentials to request headers or body",
                "priority": "P0",
                "effort": "low",
                "description": "Replace Query() params for password/username with Header() or use POST with Pydantic body model.",
                "code_example": "password: str = Header(..., alias='X-API-Key')"
            })
        
        return AIEnrichedReport(
            scan_id=evidence.scan_id,
            ai_status="completed",
            engine_used="mock",
            summary=mock_summary,
            root_causes=mock_causes,
            recommendations=mock_recommendations,
            risk_score=85 if has_critical else 25,
            confidence=0.95,
            suggested_next_checks=["security_headers", "rate_limiting"],
            notable_anomalies=list(evidence.risk_triggers),
        )
    
    def _parse_ai_response(
        self,
        scan_id: str,
        response: Dict[str, Any],
        engine: str
    ) -> AIEnrichedReport:
        """Parsea respuesta de IA a AIEnrichedReport"""
        return AIEnrichedReport(
            scan_id=scan_id,
            ai_status="completed",
            engine_used=engine,
            summary=response.get("summary", ""),
            root_causes=response.get("root_causes", []),
            recommendations=response.get("recommendations", []),
            risk_score=response.get("risk_score", 0),
            confidence=response.get("confidence", 0.0),
            suggested_next_checks=response.get("suggested_next_checks", []),
            notable_anomalies=response.get("notable_anomalies", []),
        )
    
    def _dict_to_report(self, scan_id: str, data: Dict[str, Any]) -> AIEnrichedReport:
        """Convierte dict (de cache) a AIEnrichedReport"""
        return AIEnrichedReport(
            scan_id=scan_id,
            ai_status=data.get("ai_status", "completed"),
            engine_used=data.get("engine_used"),
            summary=data.get("summary", ""),
            root_causes=data.get("root_causes", []),
            recommendations=data.get("recommendations", []),
            risk_score=data.get("risk_score", 0),
            confidence=data.get("confidence", 0.0),
            suggested_next_checks=data.get("suggested_next_checks", []),
            notable_anomalies=data.get("notable_anomalies", []),
            cached=data.get("cached", True),
        )


# Singleton
_gateway: Optional[AIGateway] = None


def get_ai_gateway() -> AIGateway:
    """Obtiene instancia singleton del gateway"""
    global _gateway
    if _gateway is None:
        _gateway = AIGateway()
    return _gateway
