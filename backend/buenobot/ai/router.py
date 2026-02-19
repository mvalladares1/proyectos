"""
BUENOBOT v3.0 - AI Router

Decide qué motor de IA usar basado en el contenido del scan.
Implementa la lógica híbrida Local vs API.
"""
import logging
from typing import Optional, List
from dataclasses import dataclass

from ..config import get_ai_config

logger = logging.getLogger(__name__)


@dataclass
class EngineSelection:
    """Resultado de selección de motor"""
    engine: str  # "local", "openai", "anthropic", "mock"
    reason: str
    complexity_score: int = 0


class AIRouter:
    """
    Router que decide entre motores de IA.
    
    Política por defecto:
    - Usar LOCAL siempre que sea posible (económico, rápido)
    - Usar API (OpenAI/Anthropic) SOLO cuando:
      a) Hay findings HIGH/CRITICAL
      b) Hay triggers de complejidad
      c) Usuario fuerza analysis_mode=deep
    """
    
    def __init__(self):
        self.config = get_ai_config()
    
    def _get_preferred_api_engine(self) -> Optional[str]:
        """Retorna el motor API preferido (anthropic > openai)"""
        if self.config.default_engine == "anthropic" and self.config.anthropic_api_key:
            return "anthropic"
        if self.config.default_engine == "openai" and self.config.openai_api_key:
            return "openai"
        # Fallback: usar el que tenga key configurada
        if self.config.anthropic_api_key:
            return "anthropic"
        if self.config.openai_api_key:
            return "openai"
        return None
    
    def select_engine(
        self,
        evidence: "EvidencePack",  # Forward reference
        analysis_mode: str = "basic"
    ) -> EngineSelection:
        """
        Selecciona el motor apropiado basado en evidence y modo.
        
        Args:
            evidence: EvidencePack del scan
            analysis_mode: "basic" o "deep"
        
        Returns:
            EngineSelection con motor y razón
        """
        # Si el modo local está en mock, siempre usar mock
        if self.config.local_engine_mode == "mock" and self.config.default_engine == "mock":
            return EngineSelection(
                engine="mock",
                reason="Development mode (mock)"
            )
        
        # Obtener motor API preferido
        preferred_api = self._get_preferred_api_engine()
        
        # Si no hay API key de ningún tipo, usar local
        if not preferred_api:
            return EngineSelection(
                engine="local" if self.config.local_engine_mode == "http" else "mock",
                reason="No API key configured (OpenAI/Anthropic)"
            )
        
        # Calcular complejidad
        complexity_score = self._calculate_complexity(evidence)
        
        # Decisión forzada por modo deep
        if analysis_mode == "deep":
            return EngineSelection(
                engine=preferred_api,
                reason=f"Deep analysis mode requested (using {preferred_api})",
                complexity_score=complexity_score
            )
        
        # Verificar si hay findings críticos
        has_critical = self._has_critical_findings(evidence)
        if has_critical and self.config.use_api_for_critical:
            return EngineSelection(
                engine=preferred_api,
                reason=f"Critical/High findings detected (using {preferred_api})",
                complexity_score=complexity_score
            )
        
        # Verificar triggers de complejidad
        complexity_triggers = self._get_complexity_triggers(evidence)
        if complexity_triggers and self.config.use_api_for_complex:
            return EngineSelection(
                engine=preferred_api,
                reason=f"Complexity triggers: {', '.join(complexity_triggers)} (using {preferred_api})",
                complexity_score=complexity_score
            )
        
        # Por defecto: usar local
        return EngineSelection(
            engine="local" if self.config.local_engine_mode == "http" else "mock",
            reason="Default local analysis (no critical issues)",
            complexity_score=complexity_score
        )
    
    def _calculate_complexity(self, evidence: "EvidencePack") -> int:
        """Calcula score de complejidad (0-100)"""
        score = 0
        
        # +10 por cada finding crítico/alto
        for finding in evidence.top_findings:
            severity = finding.get("severity", "").lower()
            if severity == "critical":
                score += 15
            elif severity == "high":
                score += 10
            elif severity == "medium":
                score += 5
        
        # +5 por cada trigger de riesgo
        score += len(evidence.risk_triggers) * 5
        
        # +10 por muchas violaciones de contrato
        if len(evidence.contract_violations) > 5:
            score += 10
        
        # +10 por muchos issues AST
        if len(evidence.backend_ast_issues) > 10:
            score += 10
        
        return min(score, 100)
    
    def _has_critical_findings(self, evidence: "EvidencePack") -> bool:
        """Verifica si hay findings críticos o altos"""
        for finding in evidence.top_findings:
            severity = finding.get("severity", "").lower()
            if severity in ["critical", "high"]:
                return True
        return False
    
    def _get_complexity_triggers(self, evidence: "EvidencePack") -> List[str]:
        """Obtiene triggers de complejidad presentes"""
        triggers = []
        
        for trigger in self.config.complexity_triggers:
            if trigger in evidence.risk_triggers:
                triggers.append(trigger)
        
        # Verificar combinaciones complejas
        if len(evidence.top_findings) > 10:
            triggers.append("many_findings")
        
        if len(evidence.contract_violations) > 0 and len(evidence.backend_ast_issues) > 0:
            triggers.append("mixed_issue_types")
        
        return triggers
