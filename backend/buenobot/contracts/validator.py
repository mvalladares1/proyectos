"""
BUENOBOT v2.0 - Contract Validator

Orquestador de validación de contratos.
Ejecuta validaciones contra endpoints reales y genera reportes.
"""
import asyncio
import httpx
import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from .schema import EndpointContract, ContractRule, get_contract_registry
from .rules import RuleEvaluator, RuleViolation

logger = logging.getLogger(__name__)


class ValidationResult:
    """Resultado de validación de un endpoint"""
    
    def __init__(
        self,
        endpoint: str,
        method: str,
        passed: bool,
        violations: List[RuleViolation],
        rules_checked: int,
        duration_ms: float,
        response_status: Optional[int] = None,
        error: Optional[str] = None
    ):
        self.endpoint = endpoint
        self.method = method
        self.passed = passed
        self.violations = violations
        self.rules_checked = rules_checked
        self.duration_ms = duration_ms
        self.response_status = response_status
        self.error = error
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "endpoint": self.endpoint,
            "method": self.method,
            "passed": self.passed,
            "violations": [v.to_dict() for v in self.violations],
            "rules_checked": self.rules_checked,
            "duration_ms": self.duration_ms,
            "response_status": self.response_status,
            "error": self.error,
            "timestamp": self.timestamp.isoformat()
        }


class ContractValidator:
    """
    Motor de validación de contratos de output.
    
    Responsabilidades:
    - Ejecutar requests a endpoints
    - Validar respuestas contra contratos YAML
    - Generar reporte de violaciones
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        timeout: float = 30.0,
        auth_credentials: Optional[Dict[str, str]] = None
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.auth_credentials = auth_credentials or {}
        self.evaluator = RuleEvaluator()
        self.registry = get_contract_registry()
    
    async def validate_endpoint(
        self,
        contract: EndpointContract,
        test_params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> ValidationResult:
        """
        Valida un endpoint contra su contrato.
        
        Args:
            contract: Contrato del endpoint
            test_params: Parámetros de prueba (query params para GET, body para POST)
            headers: Headers adicionales
        
        Returns:
            ValidationResult con estado y violaciones
        """
        start_time = time.time()
        violations: List[RuleViolation] = []
        rules_checked = 0
        response_status = None
        error = None
        
        # Preparar params
        params = test_params or {}
        # Agregar credenciales si existen
        if self.auth_credentials:
            params.update(self.auth_credentials)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.base_url}{contract.endpoint}"
                
                if contract.method.upper() == "GET":
                    response = await client.get(url, params=params, headers=headers)
                elif contract.method.upper() == "POST":
                    response = await client.post(url, json=params, headers=headers)
                else:
                    response = await client.request(
                        contract.method.upper(),
                        url,
                        params=params,
                        headers=headers
                    )
                
                response_status = response.status_code
                
                # Solo validar si status code está en los esperados
                if response_status not in contract.response_codes:
                    error = f"Status code {response_status} no esperado"
                    return ValidationResult(
                        endpoint=contract.endpoint,
                        method=contract.method,
                        passed=False,
                        violations=violations,
                        rules_checked=0,
                        duration_ms=(time.time() - start_time) * 1000,
                        response_status=response_status,
                        error=error
                    )
                
                # Parsear response
                try:
                    data = response.json()
                except:
                    data = response.text
                
                # Evaluar cada regla del contrato
                for rule in contract.rules:
                    if not rule.enabled:
                        continue
                    
                    rules_checked += 1
                    passed, rule_violations = self.evaluator.evaluate(
                        rule_type=rule.rule_type,
                        data=data,
                        field_path=rule.field_path,
                        params=rule.params,
                        request_params=params
                    )
                    
                    violations.extend(rule_violations)
                
                # Evaluar filter validations
                for fv in contract.filter_validations:
                    rules_checked += 1
                    passed, fv_violations = self.evaluator.evaluate(
                        rule_type="respects_filter",
                        data=data,
                        field_path=fv.get("response_field", "$"),
                        params=fv,
                        request_params=params
                    )
                    violations.extend(fv_violations)
                
        except httpx.TimeoutException:
            error = f"Timeout después de {self.timeout}s"
        except httpx.ConnectError:
            error = f"No se pudo conectar a {self.base_url}"
        except Exception as e:
            error = f"Error: {str(e)}"
            logger.exception(f"Error validando {contract.endpoint}")
        
        duration_ms = (time.time() - start_time) * 1000
        
        return ValidationResult(
            endpoint=contract.endpoint,
            method=contract.method,
            passed=len(violations) == 0 and error is None,
            violations=violations,
            rules_checked=rules_checked,
            duration_ms=duration_ms,
            response_status=response_status,
            error=error
        )
    
    async def validate_all_contracts(
        self,
        test_params_map: Optional[Dict[str, Dict[str, Any]]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> List[ValidationResult]:
        """
        Valida todos los contratos registrados.
        
        Args:
            test_params_map: Mapa de endpoint -> test_params
            headers: Headers comunes
        
        Returns:
            Lista de ValidationResult
        """
        self.registry.load_contracts()
        contracts = self.registry.get_all_contracts()
        
        results = []
        test_params_map = test_params_map or {}
        
        for key, contract in contracts.items():
            test_params = test_params_map.get(contract.endpoint, {})
            result = await self.validate_endpoint(contract, test_params, headers)
            results.append(result)
        
        return results
    
    def validate_data(
        self,
        contract: EndpointContract,
        data: Any,
        request_params: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Valida datos ya obtenidos contra un contrato (sin hacer request).
        Útil para validación inline durante desarrollo.
        """
        start_time = time.time()
        violations: List[RuleViolation] = []
        rules_checked = 0
        
        request_params = request_params or {}
        
        for rule in contract.rules:
            if not rule.enabled:
                continue
            
            rules_checked += 1
            passed, rule_violations = self.evaluator.evaluate(
                rule_type=rule.rule_type,
                data=data,
                field_path=rule.field_path,
                params=rule.params,
                request_params=request_params
            )
            violations.extend(rule_violations)
        
        for fv in contract.filter_validations:
            rules_checked += 1
            passed, fv_violations = self.evaluator.evaluate(
                rule_type="respects_filter",
                data=data,
                field_path=fv.get("response_field", "$"),
                params=fv,
                request_params=request_params
            )
            violations.extend(fv_violations)
        
        return ValidationResult(
            endpoint=contract.endpoint,
            method=contract.method,
            passed=len(violations) == 0,
            violations=violations,
            rules_checked=rules_checked,
            duration_ms=(time.time() - start_time) * 1000,
            response_status=200  # Asumido ya que tenemos data
        )
    
    def generate_violations_report(
        self,
        results: List[ValidationResult],
        include_passed: bool = False
    ) -> Dict[str, Any]:
        """Genera reporte consolidado de violaciones"""
        
        failed = [r for r in results if not r.passed]
        passed = [r for r in results if r.passed]
        
        total_violations = sum(len(r.violations) for r in failed)
        
        # Agrupar por severidad
        by_severity = {"critical": [], "high": [], "medium": [], "low": []}
        for result in failed:
            for v in result.violations:
                severity = v.context.get("severity", "high") if v.context else "high"
                by_severity.get(severity, by_severity["high"]).append({
                    "endpoint": result.endpoint,
                    **v.to_dict()
                })
        
        report = {
            "summary": {
                "total_endpoints": len(results),
                "passed": len(passed),
                "failed": len(failed),
                "total_violations": total_violations,
                "pass_rate": f"{len(passed)/len(results)*100:.1f}%" if results else "N/A"
            },
            "violations_by_severity": by_severity,
            "failed_endpoints": [
                {
                    "endpoint": r.endpoint,
                    "method": r.method,
                    "status": r.response_status,
                    "error": r.error,
                    "violations": [v.to_dict() for v in r.violations]
                }
                for r in failed
            ]
        }
        
        if include_passed:
            report["passed_endpoints"] = [
                {"endpoint": r.endpoint, "method": r.method, "rules_checked": r.rules_checked}
                for r in passed
            ]
        
        return report
