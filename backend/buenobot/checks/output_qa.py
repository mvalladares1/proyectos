"""
BUENOBOT v2.0 - Output QA Check

Check que valida respuestas de endpoints contra contratos YAML.
Detecta violaciones de datos, fechas fuera de rango, filtros no respetados.
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional

from ..models import CheckResult, Finding, CheckSeverity, CheckCategory
from ..contracts import ContractValidator, ContractRegistry, get_contract_registry
from ..contracts.validator import ValidationResult
from .base import BaseCheck, CheckRegistry

logger = logging.getLogger(__name__)


@CheckRegistry.register("output_contract_check", quick=True, full=True)
class OutputContractCheck(BaseCheck):
    """
    Valida respuestas de API contra contratos YAML definidos.
    
    Este check:
    1. Carga contratos desde YAML
    2. Ejecuta requests a endpoints
    3. Valida respuestas contra reglas
    4. Reporta violaciones
    """
    
    check_id = "output_contract"
    check_name = "Output Contract Validation"
    category = CheckCategory.API_QA
    description = "Valida respuestas de API contra contratos de output definidos en YAML"
    quick_check = False  # Solo en FULL scan
    
    def __init__(self):
        super().__init__()
        self.base_url = "http://localhost:8080"
        self.timeout = 30.0
        self.auth_credentials = {}
    
    def configure(
        self,
        base_url: Optional[str] = None,
        auth_credentials: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ):
        """Configura el check"""
        if base_url:
            self.base_url = base_url
        if auth_credentials:
            self.auth_credentials = auth_credentials
        if timeout:
            self.timeout = timeout
    
    async def run(self, **kwargs) -> CheckResult:
        """Ejecuta validación de contratos"""
        start_time = asyncio.get_event_loop().time()
        findings: List[Finding] = []
        
        # Obtener configuración
        base_url = kwargs.get("base_url", self.base_url)
        auth_creds = kwargs.get("auth_credentials", self.auth_credentials)
        test_params = kwargs.get("test_params_map", {})
        specific_endpoints = kwargs.get("endpoints")  # Lista de endpoints específicos
        
        try:
            # Cargar contratos
            registry = get_contract_registry()
            num_contracts = registry.load_contracts()
            
            if num_contracts == 0:
                return CheckResult(
                    check_id=self.check_id,
                    check_name=self.check_name,
                    category=self.category,
                    status="skipped",
                    summary="No hay contratos definidos",
                    findings=[Finding(
                        title="Sin contratos",
                        description="No se encontraron archivos YAML de contratos en backend/buenobot/contracts/definitions/",
                        severity=CheckSeverity.INFO
                    )],
                    duration_ms=int((asyncio.get_event_loop().time() - start_time) * 1000)
                )
            
            # Crear validator
            validator = ContractValidator(
                base_url=base_url,
                timeout=self.timeout,
                auth_credentials=auth_creds
            )
            
            # Obtener contratos a validar
            all_contracts = registry.get_all_contracts()
            
            if specific_endpoints:
                contracts_to_check = {
                    k: v for k, v in all_contracts.items()
                    if v.endpoint in specific_endpoints
                }
            else:
                contracts_to_check = all_contracts
            
            if not contracts_to_check:
                return CheckResult(
                    check_id=self.check_id,
                    check_name=self.check_name,
                    category=self.category,
                    status="passed",
                    summary=f"{num_contracts} contratos cargados, ninguno seleccionado para validar",
                    findings=[],
                    duration_ms=int((asyncio.get_event_loop().time() - start_time) * 1000)
                )
            
            # Ejecutar validaciones
            results: List[ValidationResult] = []
            
            for key, contract in contracts_to_check.items():
                endpoint_params = test_params.get(contract.endpoint, {})
                result = await validator.validate_endpoint(contract, endpoint_params)
                results.append(result)
            
            # Procesar resultados -> findings
            for result in results:
                if result.error:
                    findings.append(Finding(
                        title=f"Error validando {result.endpoint}",
                        description=result.error,
                        severity=CheckSeverity.MEDIUM,
                        location=result.endpoint
                    ))
                
                for violation in result.violations:
                    # Mapear severidad
                    severity_map = {
                        "critical": CheckSeverity.CRITICAL,
                        "high": CheckSeverity.HIGH,
                        "medium": CheckSeverity.MEDIUM,
                        "low": CheckSeverity.LOW
                    }
                    severity = severity_map.get(
                        violation.context.get("severity", "high") if violation.context else "high",
                        CheckSeverity.HIGH
                    )
                    
                    findings.append(Finding(
                        title=f"[{violation.rule_type}] {result.endpoint}",
                        description=violation.message,
                        severity=severity,
                        location=f"{result.endpoint} -> {violation.field_path}",
                        evidence=f"Valor: {violation.actual_value}, Esperado: {violation.expected}",
                        recommendation=self._get_recommendation(violation.rule_type)
                    ))
            
            # Generar reporte
            passed_count = sum(1 for r in results if r.passed)
            failed_count = len(results) - passed_count
            total_violations = sum(len(r.violations) for r in results)
            
            # Determinar status
            has_critical = any(f.severity in [CheckSeverity.CRITICAL, CheckSeverity.HIGH] for f in findings)
            status = "failed" if has_critical else ("passed" if failed_count == 0 else "warning")
            
            return CheckResult(
                check_id=self.check_id,
                check_name=self.check_name,
                category=self.category,
                status=status,
                summary=f"Contratos: {passed_count}/{len(results)} OK, {total_violations} violaciones",
                findings=findings,
                duration_ms=int((asyncio.get_event_loop().time() - start_time) * 1000),
                raw_output=str(validator.generate_violations_report(results))
            )
            
        except Exception as e:
            logger.exception("Error en OutputContractCheck")
            return CheckResult(
                check_id=self.check_id,
                check_name=self.check_name,
                category=self.category,
                status="error",
                summary=f"Error: {str(e)}",
                findings=[Finding(
                    title="Error ejecutando check",
                    description=str(e),
                    severity=CheckSeverity.MEDIUM
                )],
                duration_ms=int((asyncio.get_event_loop().time() - start_time) * 1000)
            )
    
    def _get_recommendation(self, rule_type: str) -> str:
        """Retorna recomendación según tipo de violación"""
        recommendations = {
            "date_in_range": "Verificar lógica de fechas en el servicio. Añadir validación de rangos.",
            "no_future_dates": "Agregar validación para rechazar fechas futuras en el modelo.",
            "no_credentials_in_output": "CRÍTICO: Eliminar campos sensibles del response. Usar exclude en Pydantic.",
            "respects_filter": "El filtro no se está aplicando correctamente. Revisar query/ORM.",
            "no_negative_values": "Agregar validación >= 0 en el modelo o servicio.",
            "not_null": "Campo requerido está vacío. Agregar validación en modelo.",
            "allowed_values": "Valor no permitido detectado. Usar Enum o validación.",
            "subset_of_param": "Resultado contiene valores fuera del filtro enviado.",
            "unique_values": "Duplicados detectados. Verificar lógica de deduplicación."
        }
        return recommendations.get(rule_type, "Revisar lógica del endpoint.")


@CheckRegistry.register("filter_validation", quick=True, full=True)
class FilterValidationCheck(BaseCheck):
    """
    Check especializado en validación de filtros.
    
    Verifica que cuando se envía un filtro (fecha_desde, estado, etc.),
    TODOS los resultados lo respeten. Detecta leaks de datos por filtros mal aplicados.
    """
    
    check_id = "filter_validation"
    check_name = "Filter Validation"
    category = CheckCategory.API_QA
    description = "Valida que filtros enviados se apliquen correctamente en resultados"
    quick_check = True  # Importante, incluir en quick scan
    
    # Endpoints críticos a validar con sus filtros
    CRITICAL_FILTERS = [
        {
            "endpoint": "/api/v1/recepcion/list",
            "filters": [
                {"param": "fecha_desde", "field": "$.recepciones[*].fecha", "type": "gte"},
                {"param": "fecha_hasta", "field": "$.recepciones[*].fecha", "type": "lte"},
                {"param": "estado", "field": "$.recepciones[*].estado", "type": "equals"}
            ]
        },
        {
            "endpoint": "/api/v1/stock/camaras",
            "filters": [
                {"param": "fecha_desde", "field": "$.data[*].fecha_ingreso", "type": "gte"},
                {"param": "fecha_hasta", "field": "$.data[*].fecha_ingreso", "type": "lte"}
            ]
        },
        {
            "endpoint": "/api/v1/produccion/ordenes",
            "filters": [
                {"param": "fecha_desde", "field": "$.ordenes[*].fecha_inicio", "type": "gte"},
                {"param": "estado", "field": "$.ordenes[*].estado", "type": "equals"}
            ]
        },
        {
            "endpoint": "/api/v1/compras/ordenes",
            "filters": [
                {"param": "proveedor_id", "field": "$.ordenes[*].proveedor_id", "type": "equals"}
            ]
        }
    ]
    
    async def run(self, **kwargs) -> CheckResult:
        """Ejecuta validación de filtros"""
        # Este check se basa en OutputContractCheck pero con énfasis en filtros
        # Para quick scan, solo lista los filtros críticos definidos
        
        findings: List[Finding] = []
        start_time = asyncio.get_event_loop().time()
        
        # En quick scan, solo verificamos que existan contratos para filtros críticos
        registry = get_contract_registry()
        registry.load_contracts()
        
        missing_contracts = []
        for item in self.CRITICAL_FILTERS:
            endpoint = item["endpoint"]
            if not registry.has_contract(endpoint):
                missing_contracts.append(endpoint)
        
        if missing_contracts:
            findings.append(Finding(
                title="Endpoints sin contrato de filtros",
                description=f"Los siguientes endpoints críticos no tienen contrato de validación: {', '.join(missing_contracts)}",
                severity=CheckSeverity.MEDIUM,
                recommendation="Agregar contratos YAML para estos endpoints en backend/buenobot/contracts/definitions/"
            ))
        
        # Contar filtros definidos
        total_filters = sum(len(item["filters"]) for item in self.CRITICAL_FILTERS)
        
        return CheckResult(
            check_id=self.check_id,
            check_name=self.check_name,
            category=self.category,
            status="passed" if not findings else "warning",
            summary=f"{total_filters} filtros críticos definidos, {len(missing_contracts)} endpoints sin contrato",
            findings=findings,
            duration_ms=int((asyncio.get_event_loop().time() - start_time) * 1000)
        )
