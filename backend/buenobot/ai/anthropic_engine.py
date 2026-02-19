"""
BUENOBOT v3.0 - Anthropic/Claude Engine

Motor de IA usando Anthropic Claude API.
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


class AnthropicEngine:
    """
    Motor de IA usando Anthropic Claude API.
    
    Características:
    - Usa Claude Messages API
    - Sanitiza requests/responses
    - Maneja timeouts y errores
    """
    
    def __init__(self):
        self.config = get_ai_config()
        self.sanitizer = get_sanitizer()
    
    async def generate(self, evidence: "EvidencePack") -> Dict[str, Any]:
        """
        Genera análisis usando Anthropic Claude API.
        
        Args:
            evidence: EvidencePack del scan
        
        Returns:
            Dict con campos: summary, root_causes, recommendations, etc.
        """
        if not self.config.anthropic_api_key:
            raise ValueError("Anthropic API key not configured")
        
        # Importar httpx aquí para evitar dependencia global
        import httpx
        
        # Construir mensajes
        system_prompt, user_message = self._build_messages(evidence)
        
        # Construir payload
        payload = {
            "model": self.config.anthropic_model,
            "max_tokens": self.config.anthropic_max_tokens,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_message}
            ]
        }
        
        headers = {
            "x-api-key": self.config.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.config.anthropic_timeout) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                
                result = response.json()
                
                # Extraer contenido (Claude devuelve array de content blocks)
                content = ""
                for block in result.get("content", []):
                    if block.get("type") == "text":
                        content = block.get("text", "")
                        break
                
                if not content:
                    logger.error("Empty response from Claude")
                    return self._fallback_response(evidence)
                
                # Parsear JSON (Claude puede incluir markdown, limpiar)
                try:
                    # Intentar extraer JSON de posible code block
                    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', content)
                    if json_match:
                        content = json_match.group(1).strip()
                    
                    # Intentar encontrar objeto JSON directamente
                    json_start = content.find('{')
                    json_end = content.rfind('}')
                    if json_start >= 0 and json_end > json_start:
                        content = content[json_start:json_end + 1]
                    
                    ai_response = json.loads(content)
                    return self._validate_response(ai_response)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse Claude JSON response: {e}")
                    logger.debug(f"Raw content: {content[:500]}...")
                    return self._fallback_response(evidence)
                    
        except httpx.TimeoutException:
            logger.error(f"Claude timeout after {self.config.anthropic_timeout}s")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"Anthropic HTTP error: {e.response.status_code}")
            # Sanitizar error para no exponer info sensible
            error_body = self.sanitizer.sanitize_string(str(e.response.text))
            logger.error(f"Error body: {error_body[:500]}")
            raise
        except Exception as e:
            logger.exception(f"Anthropic engine error: {e}")
            raise
    
    def _build_messages(self, evidence: "EvidencePack") -> tuple:
        """Construye system prompt y user message para Claude"""
        
        # System prompt
        system_prompt = """You are BUENOBOT, an expert security and code quality analyst for the Rio Futuro Dashboards project.
You analyze scan results and provide actionable insights.

CRITICAL RULES:
1. NEVER hallucinate - only reference evidence from the provided EvidencePack
2. Always cite finding IDs when making claims
3. Be concise and actionable
4. Output ONLY valid JSON (no markdown, no explanations outside JSON structure)
5. Never suggest running commands or directly accessing systems
6. The PASS/WARN/FAIL gate is already determined - you explain why and suggest fixes
7. Prioritize security issues (credentials, injection, data leaks) as P0

You MUST respond with ONLY a JSON object matching this exact schema:
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
}

DO NOT include any text before or after the JSON object. Start directly with { and end with }."""
        
        # User prompt con evidence
        user_prompt = self._format_evidence(evidence)
        
        return (system_prompt, user_prompt)
    
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
        
        parts.append("\n---\nAnalyze this evidence and respond with ONLY the JSON object. No explanation before or after.")
        
        return "\n".join(parts)
    
    def _validate_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Valida y normaliza respuesta de Claude"""
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
