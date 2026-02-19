"""
BUENOBOT v3.0 - Local LLM Engine

Motor local para análisis IA.
Soporta modo mock (desarrollo) y modo http (Ollama/LMStudio/etc).
"""
import asyncio
import logging
import json
import httpx
from typing import Dict, Any, Optional

from ..config import get_ai_config

logger = logging.getLogger(__name__)


class LocalEngine:
    """
    Motor de IA local.
    
    Modos:
    - mock: Genera respuestas dummy para desarrollo
    - http: Llama a endpoint local (Ollama, LMStudio, etc.)
    """
    
    def __init__(self):
        self.config = get_ai_config()
    
    async def generate(self, evidence: "EvidencePack") -> Dict[str, Any]:
        """
        Genera análisis usando motor local.
        
        Args:
            evidence: EvidencePack del scan
        
        Returns:
            Dict con campos: summary, root_causes, recommendations, etc.
        """
        if self.config.local_engine_mode == "mock":
            return await self._generate_mock(evidence)
        else:
            return await self._generate_http(evidence)
    
    async def _generate_mock(self, evidence: "EvidencePack") -> Dict[str, Any]:
        """Genera respuesta mock para desarrollo"""
        await asyncio.sleep(0.3)  # Simular latencia
        
        # Analizar evidence para generar respuesta realista
        findings_count = len(evidence.top_findings)
        has_security = "password_in_query_params" in evidence.risk_triggers
        
        summary = f"Analysis of scan {evidence.scan_id}: "
        if findings_count == 0:
            summary += "No significant issues detected. Code quality is acceptable."
        else:
            summary += f"Found {findings_count} issues. "
            if has_security:
                summary += "SECURITY ALERT: Sensitive data exposure detected."
        
        root_causes = []
        recommendations = []
        
        # Generar root causes basados en triggers
        if "password_in_query_params" in evidence.risk_triggers:
            root_causes.append({
                "cause": "Legacy authentication pattern",
                "evidence_ids": ["finding_1"],
                "severity": "critical",
                "explanation": "Authentication credentials are passed via URL query parameters, "
                              "which exposes them in server logs, browser history, and referrer headers."
            })
            recommendations.append({
                "title": "Migrate credentials to secure transport",
                "priority": "P0",
                "effort": "medium",
                "description": "Move username/password from Query params to either:\n"
                              "1. HTTP Headers (X-API-Key, Authorization)\n"
                              "2. POST request body with Pydantic model\n"
                              "3. OAuth2 token-based authentication",
                "code_example": (
                    "# Option 1: Headers\n"
                    "@router.get('/data')\n"
                    "async def get_data(\n"
                    "    x_api_key: str = Header(...),\n"
                    "    x_username: str = Header(...)\n"
                    "):\n"
                    "    ...\n\n"
                    "# Option 2: POST body\n"
                    "class AuthRequest(BaseModel):\n"
                    "    username: str\n"
                    "    password: str\n\n"
                    "@router.post('/data')\n"
                    "async def get_data(auth: AuthRequest):\n"
                    "    ..."
                )
            })
        
        if "print_in_routers" in evidence.risk_triggers:
            root_causes.append({
                "cause": "Debug statements in production code",
                "evidence_ids": ["finding_2"],
                "severity": "low",
                "explanation": "Print statements bypass logging configuration and may leak sensitive data."
            })
            recommendations.append({
                "title": "Replace print with logging",
                "priority": "P3",
                "effort": "low",
                "description": "Replace all print() calls with proper logging using the logger module.",
                "code_example": (
                    "import logging\n"
                    "logger = logging.getLogger(__name__)\n\n"
                    "# Instead of:\n"
                    "print(f'Debug: {data}')\n\n"
                    "# Use:\n"
                    "logger.debug(f'Processing: {data}')"
                )
            })
        
        return {
            "summary": summary,
            "root_causes": root_causes,
            "recommendations": recommendations,
            "risk_score": 85 if has_security else 25,
            "confidence": 0.92,
            "suggested_next_checks": [
                "authentication_audit",
                "logging_review",
                "input_validation_check"
            ],
            "notable_anomalies": list(evidence.risk_triggers)
        }
    
    async def _generate_http(self, evidence: "EvidencePack") -> Dict[str, Any]:
        """Genera respuesta vía endpoint HTTP local (Ollama/etc)"""
        
        # Cargar prompt
        prompt = self._build_prompt(evidence)
        
        # Construir payload para Ollama
        payload = {
            "model": self.config.local_engine_model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.3,
                "num_predict": 2000
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.config.local_engine_timeout) as client:
                response = await client.post(
                    f"{self.config.local_engine_url}/api/generate",
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                
                # Parsear respuesta
                try:
                    ai_response = json.loads(result.get("response", "{}"))
                    return self._validate_response(ai_response)
                except json.JSONDecodeError:
                    logger.error("Failed to parse local LLM JSON response")
                    return self._fallback_response(evidence)
                    
        except httpx.TimeoutException:
            logger.error(f"Local engine timeout after {self.config.local_engine_timeout}s")
            raise
        except httpx.HTTPError as e:
            logger.error(f"Local engine HTTP error: {e}")
            raise
        except Exception as e:
            logger.exception(f"Local engine error: {e}")
            raise
    
    def _build_prompt(self, evidence: "EvidencePack") -> str:
        """Construye prompt para el LLM local"""
        
        prompt = """You are BUENOBOT, analyzing a security and quality scan.

EVIDENCE PACK:
"""
        prompt += f"- Scan ID: {evidence.scan_id}\n"
        prompt += f"- Environment: {evidence.environment}\n"
        prompt += f"- Gate Status: {evidence.gate_status}\n"
        prompt += f"- Risk Triggers: {', '.join(evidence.risk_triggers) or 'None'}\n\n"
        
        if evidence.top_findings:
            prompt += "TOP FINDINGS:\n"
            for i, f in enumerate(evidence.top_findings[:10], 1):
                prompt += f"{i}. [{f.get('severity', 'unknown').upper()}] {f.get('title', 'Unknown')}\n"
                prompt += f"   Location: {f.get('location', 'N/A')}\n"
            prompt += "\n"
        
        prompt += """
OUTPUT (JSON only):
{
    "summary": "Brief analysis summary",
    "root_causes": [{"cause": "...", "evidence_ids": [...], "severity": "...", "explanation": "..."}],
    "recommendations": [{"title": "...", "priority": "P0-P4", "effort": "low|medium|high", "description": "...", "code_example": "..."}],
    "risk_score": 0-100,
    "confidence": 0.0-1.0,
    "suggested_next_checks": ["..."],
    "notable_anomalies": ["..."]
}
"""
        return prompt
    
    def _validate_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Valida y normaliza respuesta del LLM"""
        return {
            "summary": response.get("summary", "Analysis completed"),
            "root_causes": response.get("root_causes", []),
            "recommendations": response.get("recommendations", []),
            "risk_score": min(100, max(0, response.get("risk_score", 50))),
            "confidence": min(1.0, max(0.0, response.get("confidence", 0.5))),
            "suggested_next_checks": response.get("suggested_next_checks", []),
            "notable_anomalies": response.get("notable_anomalies", [])
        }
    
    def _fallback_response(self, evidence: "EvidencePack") -> Dict[str, Any]:
        """Respuesta de fallback cuando el parsing falla"""
        return {
            "summary": f"Analysis completed for scan {evidence.scan_id}",
            "root_causes": [],
            "recommendations": [],
            "risk_score": 50,
            "confidence": 0.3,
            "suggested_next_checks": [],
            "notable_anomalies": list(evidence.risk_triggers)
        }
