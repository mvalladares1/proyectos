"""
BUENOBOT v3.0 - OpenAI Engine

Motor de IA usando OpenAI API (Responses API con JSON output).
"""
import asyncio
import logging
import json
import os
import re
from typing import Dict, Any, Optional, List

from ..config import get_ai_config
from ..security import get_sanitizer

logger = logging.getLogger(__name__)


class OpenAIEngine:
    """
    Motor de IA usando OpenAI API.
    
    Características:
    - Usa Responses API con structured output
    - Sanitiza requests/responses
    - Maneja timeouts y errores
    """
    
    def __init__(self):
        self.config = get_ai_config()
        self.sanitizer = get_sanitizer()
    
    async def generate(self, evidence: "EvidencePack") -> Dict[str, Any]:
        """
        Genera análisis usando OpenAI API.
        
        Args:
            evidence: EvidencePack del scan
        
        Returns:
            Dict con campos: summary, root_causes, recommendations, etc.
        """
        if not self.config.openai_api_key:
            raise ValueError("OpenAI API key not configured")
        
        # Importar httpx aquí para evitar dependencia global
        import httpx
        
        # Construir mensajes
        messages = self._build_messages(evidence)
        
        # Construir payload
        payload = {
            "model": self.config.openai_model,
            "messages": messages,
            "max_tokens": self.config.openai_max_tokens,
            "temperature": 0.3,
            "response_format": {"type": "json_object"}
        }
        
        headers = {
            "Authorization": f"Bearer {self.config.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.config.openai_timeout) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                
                result = response.json()
                
                # Extraer contenido
                content = result["choices"][0]["message"]["content"]
                
                # Parsear JSON
                try:
                    ai_response = json.loads(content)
                    return self._validate_response(ai_response)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse OpenAI JSON response: {e}")
                    logger.debug(f"Raw content: {content[:500]}...")
                    return self._fallback_response(evidence)
                    
        except httpx.TimeoutException:
            logger.error(f"OpenAI timeout after {self.config.openai_timeout}s")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI HTTP error: {e.response.status_code}")
            # Sanitizar error para no exponer info sensible
            error_body = self.sanitizer.sanitize_string(str(e.response.text))
            logger.error(f"Error body: {error_body[:500]}")
            raise
        except Exception as e:
            logger.exception(f"OpenAI engine error: {e}")
            raise
    
    def _build_messages(self, evidence: "EvidencePack") -> List[Dict[str, str]]:
        """Construye mensajes para la API de OpenAI"""
        
        # System prompt
        system_prompt = """You are BUENOBOT, an expert security and code quality analyst for the Rio Futuro Dashboards project.
You analyze scan results and provide actionable insights.

CRITICAL RULES:
1. NEVER hallucinate - only reference evidence from the provided EvidencePack
2. Always cite finding IDs when making claims
3. Be concise and actionable
4. Output valid JSON only (no markdown, no explanations outside JSON)
5. Never suggest running commands or directly accessing systems
6. The PASS/WARN/FAIL gate is already determined - you explain why and suggest fixes
7. Prioritize security issues (credentials, injection, data leaks) as P0

OUTPUT SCHEMA (strict JSON):
{
    "summary": "One paragraph executive summary of the scan results",
    "root_causes": [
        {
            "cause": "Brief description of root cause",
            "evidence_ids": ["finding_id_1", "finding_id_2"],
            "severity": "critical|high|medium|low",
            "explanation": "Technical explanation"
        }
    ],
    "recommendations": [
        {
            "title": "Action title",
            "priority": "P0|P1|P2|P3|P4",
            "effort": "low|medium|high",
            "description": "Detailed description",
            "code_example": "Optional code fix example"
        }
    ],
    "risk_score": 0-100,
    "confidence": 0.0-1.0,
    "suggested_next_checks": ["check_name_1", "check_name_2"],
    "notable_anomalies": ["anomaly_1", "anomaly_2"]
}"""
        
        # User prompt con evidence
        user_prompt = self._format_evidence(evidence)
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    
    def _format_evidence(self, evidence: "EvidencePack") -> str:
        """Formatea EvidencePack para el prompt"""
        
        # Sanitizar antes de enviar
        parts = []
        
        parts.append("# EVIDENCE PACK FOR ANALYSIS\n")
        parts.append(f"Scan ID: {evidence.scan_id}")
        parts.append(f"Environment: {evidence.environment}")
        parts.append(f"Scan Type: {evidence.scan_type}")
        parts.append(f"Commit SHA: {evidence.commit_sha or 'unknown'}")
        parts.append(f"Gate Status: {evidence.gate_status}")
        parts.append(f"Timestamp: {evidence.created_at}")
        parts.append("")
        
        # Checklist
        if evidence.checklist:
            parts.append("## CHECKLIST")
            for key, value in evidence.checklist.items():
                status = "✓" if value else "✗"
                parts.append(f"  {status} {key}")
            parts.append("")
        
        # Risk triggers
        if evidence.risk_triggers:
            parts.append("## RISK TRIGGERS")
            for trigger in evidence.risk_triggers:
                parts.append(f"  - {trigger}")
            parts.append("")
        
        # Top findings (limitados)
        if evidence.top_findings:
            parts.append("## TOP FINDINGS")
            for i, finding in enumerate(evidence.top_findings[:self.config.max_findings_to_ai], 1):
                parts.append(f"\n### Finding {i} (ID: finding_{i})")
                parts.append(f"  Title: {finding.get('title', 'Unknown')}")
                parts.append(f"  Severity: {finding.get('severity', 'unknown').upper()}")
                parts.append(f"  Location: {finding.get('location', 'N/A')}")
                if finding.get('description'):
                    desc = finding['description'][:300]
                    parts.append(f"  Description: {desc}")
                if finding.get('evidence'):
                    evidence_text = self.sanitizer.sanitize_string(finding['evidence'][:200])
                    parts.append(f"  Evidence: {evidence_text}")
            parts.append("")
        
        # Contract violations
        if evidence.contract_violations:
            parts.append("## CONTRACT VIOLATIONS")
            for i, cv in enumerate(evidence.contract_violations[:10], 1):
                parts.append(f"  {i}. {cv.get('endpoint', 'Unknown')}: {cv.get('message', '')}")
            parts.append("")
        
        # AST issues
        if evidence.backend_ast_issues:
            parts.append("## CODE DESIGN ISSUES (AST)")
            for i, issue in enumerate(evidence.backend_ast_issues[:10], 1):
                parts.append(f"  {i}. [{issue.get('rule', '?')}] {issue.get('message', '')}")
                parts.append(f"     File: {issue.get('file_path', 'unknown')}:{issue.get('line_number', '?')}")
            parts.append("")
        
        # Performance metrics
        if evidence.performance_metrics:
            parts.append("## PERFORMANCE METRICS")
            for key, value in evidence.performance_metrics.items():
                parts.append(f"  {key}: {value}")
            parts.append("")
        
        parts.append("\n---\nAnalyze this evidence and provide your assessment in JSON format.")
        
        return "\n".join(parts)
    
    def _validate_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Valida y normaliza respuesta de OpenAI"""
        return {
            "summary": str(response.get("summary", "Analysis completed")),
            "root_causes": response.get("root_causes", []),
            "recommendations": response.get("recommendations", []),
            "risk_score": min(100, max(0, int(response.get("risk_score", 50)))),
            "confidence": min(1.0, max(0.0, float(response.get("confidence", 0.7)))),
            "suggested_next_checks": response.get("suggested_next_checks", []),
            "notable_anomalies": response.get("notable_anomalies", [])
        }
    
    def _fallback_response(self, evidence: "EvidencePack") -> Dict[str, Any]:
        """Respuesta de fallback cuando el parsing falla"""
        return {
            "summary": f"Analysis completed for scan {evidence.scan_id} (parsing error)",
            "root_causes": [],
            "recommendations": [],
            "risk_score": 50,
            "confidence": 0.3,
            "suggested_next_checks": [],
            "notable_anomalies": list(evidence.risk_triggers)
        }
