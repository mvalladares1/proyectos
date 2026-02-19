"""
BUENOBOT v2.0 - Rule Evaluators

Implementación de cada tipo de regla de validación.
Cada evaluador recibe datos y parámetros, retorna (passed, violations)
"""
from datetime import datetime, date, timedelta
from typing import Any, List, Dict, Tuple, Optional, Callable
import re
import logging
from jsonpath_ng import parse as jsonpath_parse
from jsonpath_ng.exceptions import JsonPathParserError

logger = logging.getLogger(__name__)


# Campos sensibles que no deben aparecer en outputs
SENSITIVE_FIELDS = [
    'password', 'passwd', 'pwd', 'secret', 'token', 'api_key', 'apikey',
    'access_token', 'refresh_token', 'bearer', 'credential', 'private_key',
    'ssh_key', 'auth_token', 'session_id', 'sessionid'
]


class RuleViolation:
    """Representa una violación de regla detectada"""
    
    def __init__(
        self,
        rule_type: str,
        field_path: str,
        message: str,
        actual_value: Any = None,
        expected: Any = None,
        context: Optional[Dict[str, Any]] = None
    ):
        self.rule_type = rule_type
        self.field_path = field_path
        self.message = message
        self.actual_value = actual_value
        self.expected = expected
        self.context = context or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_type": self.rule_type,
            "field_path": self.field_path,
            "message": self.message,
            "actual_value": str(self.actual_value)[:200] if self.actual_value else None,
            "expected": str(self.expected)[:200] if self.expected else None,
            "context": self.context
        }


class RuleEvaluator:
    """
    Motor de evaluación de reglas.
    Aplica reglas sobre datos JSON y retorna violaciones.
    """
    
    def __init__(self):
        self.evaluators: Dict[str, Callable] = {
            "date_in_range": self._eval_date_in_range,
            "no_future_dates": self._eval_no_future_dates,
            "allowed_values": self._eval_allowed_values,
            "allowed_values_if": self._eval_allowed_values_if,
            "not_null": self._eval_not_null,
            "no_negative_values": self._eval_no_negative_values,
            "subset_of_param": self._eval_subset_of_param,
            "respects_filter": self._eval_respects_filter,
            "sum_equals": self._eval_sum_equals,
            "sum_equals_field": self._eval_sum_equals_field,
            "monotonic_sequence": self._eval_monotonic_sequence,
            "fields_present": self._eval_fields_present,
            "array_not_empty": self._eval_array_not_empty,
            "unique_values": self._eval_unique_values,
            "no_credentials_in_output": self._eval_no_credentials_in_output,
        }
    
    def evaluate(
        self,
        rule_type: str,
        data: Any,
        field_path: str,
        params: Dict[str, Any],
        request_params: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, List[RuleViolation]]:
        """
        Evalúa una regla sobre los datos.
        
        Args:
            rule_type: Tipo de regla a evaluar
            data: Datos JSON de la respuesta
            field_path: JSONPath al campo
            params: Parámetros de la regla
            request_params: Parámetros del request (para filter validation)
        
        Returns:
            Tuple (passed: bool, violations: List[RuleViolation])
        """
        evaluator = self.evaluators.get(rule_type)
        if not evaluator:
            logger.warning(f"Regla desconocida: {rule_type}")
            return True, []
        
        try:
            # Extraer valores usando JSONPath
            values = self._extract_values(data, field_path)
            return evaluator(values, field_path, params, request_params or {})
        except Exception as e:
            logger.error(f"Error evaluando regla {rule_type}: {e}")
            return False, [RuleViolation(
                rule_type=rule_type,
                field_path=field_path,
                message=f"Error evaluando regla: {str(e)}"
            )]
    
    def _extract_values(self, data: Any, field_path: str) -> List[Any]:
        """Extrae valores usando JSONPath"""
        try:
            # Si es "$" significa el root
            if field_path == "$" or field_path == "$.":
                return [data]
            
            jsonpath_expr = jsonpath_parse(field_path)
            matches = jsonpath_expr.find(data)
            return [match.value for match in matches]
        except JsonPathParserError as e:
            logger.error(f"JSONPath inválido '{field_path}': {e}")
            return []
    
    def _parse_date(self, value: Any) -> Optional[date]:
        """Parsea valor a fecha"""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]:
                try:
                    return datetime.strptime(value[:19], fmt).date()
                except:
                    pass
        return None
    
    # === EVALUADORES DE REGLAS ===
    
    def _eval_date_in_range(
        self, values: List, field_path: str, params: Dict, req: Dict
    ) -> Tuple[bool, List[RuleViolation]]:
        """Valida que fechas estén en rango especificado"""
        violations = []
        
        min_date_str = params.get("min_date")
        max_date_str = params.get("max_date")
        days_back = params.get("days_back")
        days_forward = params.get("days_forward", 0)
        
        today = date.today()
        min_date = None
        max_date = None
        
        if days_back:
            min_date = today - timedelta(days=days_back)
        elif min_date_str:
            min_date = self._parse_date(min_date_str)
        
        if days_forward is not None:
            max_date = today + timedelta(days=days_forward)
        elif max_date_str:
            max_date = self._parse_date(max_date_str)
        
        for val in values:
            parsed = self._parse_date(val)
            if parsed is None:
                continue
            
            if min_date and parsed < min_date:
                violations.append(RuleViolation(
                    rule_type="date_in_range",
                    field_path=field_path,
                    message=f"Fecha {val} anterior al mínimo {min_date}",
                    actual_value=val,
                    expected=f">= {min_date}"
                ))
            
            if max_date and parsed > max_date:
                violations.append(RuleViolation(
                    rule_type="date_in_range",
                    field_path=field_path,
                    message=f"Fecha {val} posterior al máximo {max_date}",
                    actual_value=val,
                    expected=f"<= {max_date}"
                ))
        
        return len(violations) == 0, violations
    
    def _eval_no_future_dates(
        self, values: List, field_path: str, params: Dict, req: Dict
    ) -> Tuple[bool, List[RuleViolation]]:
        """Valida que no haya fechas futuras"""
        violations = []
        today = date.today()
        tolerance_days = params.get("tolerance_days", 0)
        max_date = today + timedelta(days=tolerance_days)
        
        for val in values:
            parsed = self._parse_date(val)
            if parsed and parsed > max_date:
                violations.append(RuleViolation(
                    rule_type="no_future_dates",
                    field_path=field_path,
                    message=f"Fecha futura detectada: {val}",
                    actual_value=val,
                    expected=f"<= {max_date}"
                ))
        
        return len(violations) == 0, violations
    
    def _eval_allowed_values(
        self, values: List, field_path: str, params: Dict, req: Dict
    ) -> Tuple[bool, List[RuleViolation]]:
        """Valida que valores estén en lista permitida"""
        violations = []
        allowed = set(params.get("values", []))
        
        if not allowed:
            return True, []
        
        for val in values:
            if val not in allowed:
                violations.append(RuleViolation(
                    rule_type="allowed_values",
                    field_path=field_path,
                    message=f"Valor '{val}' no permitido",
                    actual_value=val,
                    expected=list(allowed)
                ))
        
        return len(violations) == 0, violations
    
    def _eval_allowed_values_if(
        self, values: List, field_path: str, params: Dict, req: Dict
    ) -> Tuple[bool, List[RuleViolation]]:
        """Valida valores permitidos condicionalmente"""
        violations = []
        
        condition_field = params.get("if_field")
        condition_values = params.get("if_values", [])
        then_allowed = set(params.get("then_allowed", []))
        
        # Si la condición no aplica, skip
        if condition_field:
            condition_val = req.get(condition_field)
            if condition_val not in condition_values:
                return True, []
        
        for val in values:
            if val not in then_allowed:
                violations.append(RuleViolation(
                    rule_type="allowed_values_if",
                    field_path=field_path,
                    message=f"Valor '{val}' no permitido cuando {condition_field}={condition_values}",
                    actual_value=val,
                    expected=list(then_allowed)
                ))
        
        return len(violations) == 0, violations
    
    def _eval_not_null(
        self, values: List, field_path: str, params: Dict, req: Dict
    ) -> Tuple[bool, List[RuleViolation]]:
        """Valida que valores no sean null/None"""
        violations = []
        
        for val in values:
            if val is None:
                violations.append(RuleViolation(
                    rule_type="not_null",
                    field_path=field_path,
                    message=f"Campo no debe ser null",
                    actual_value=None,
                    expected="valor no nulo"
                ))
        
        return len(violations) == 0, violations
    
    def _eval_no_negative_values(
        self, values: List, field_path: str, params: Dict, req: Dict
    ) -> Tuple[bool, List[RuleViolation]]:
        """Valida que no haya valores negativos"""
        violations = []
        allow_zero = params.get("allow_zero", True)
        
        for val in values:
            if isinstance(val, (int, float)):
                if val < 0 or (not allow_zero and val == 0):
                    violations.append(RuleViolation(
                        rule_type="no_negative_values",
                        field_path=field_path,
                        message=f"Valor negativo detectado: {val}",
                        actual_value=val,
                        expected=">= 0" if allow_zero else "> 0"
                    ))
        
        return len(violations) == 0, violations
    
    def _eval_subset_of_param(
        self, values: List, field_path: str, params: Dict, req: Dict
    ) -> Tuple[bool, List[RuleViolation]]:
        """Valida que valores del output sean subconjunto del parámetro enviado"""
        violations = []
        
        param_name = params.get("param_name")
        if not param_name:
            return True, []
        
        param_value = req.get(param_name)
        if param_value is None:
            # Si no se envió el parámetro, no aplica
            return True, []
        
        # Convertir a set para comparación
        if isinstance(param_value, str):
            # Podría ser lista separada por comas
            allowed = set(x.strip() for x in param_value.split(","))
        elif isinstance(param_value, list):
            allowed = set(param_value)
        else:
            allowed = {param_value}
        
        for val in values:
            if val not in allowed:
                violations.append(RuleViolation(
                    rule_type="subset_of_param",
                    field_path=field_path,
                    message=f"Valor '{val}' no está en el filtro enviado",
                    actual_value=val,
                    expected=list(allowed),
                    context={"param_name": param_name}
                ))
        
        return len(violations) == 0, violations
    
    def _eval_respects_filter(
        self, values: List, field_path: str, params: Dict, req: Dict
    ) -> Tuple[bool, List[RuleViolation]]:
        """
        Valida que si se envió un filtro, todos los resultados lo respeten.
        Ejemplo: si filtro fecha_desde=2024-01-01, ningún item puede tener fecha < 2024-01-01
        """
        violations = []
        
        filter_param = params.get("filter_param")
        filter_type = params.get("filter_type", "equals")  # equals, gte, lte, contains
        
        if not filter_param:
            return True, []
        
        filter_value = req.get(filter_param)
        if filter_value is None:
            return True, []
        
        for val in values:
            passed = self._check_filter_compliance(val, filter_value, filter_type)
            if not passed:
                violations.append(RuleViolation(
                    rule_type="respects_filter",
                    field_path=field_path,
                    message=f"Resultado viola filtro {filter_param}={filter_value}",
                    actual_value=val,
                    expected=f"{filter_type} {filter_value}",
                    context={"filter_param": filter_param, "filter_type": filter_type}
                ))
        
        return len(violations) == 0, violations
    
    def _check_filter_compliance(self, val: Any, filter_val: Any, filter_type: str) -> bool:
        """Verifica si un valor cumple con el filtro"""
        if filter_type == "equals":
            return str(val) == str(filter_val)
        
        elif filter_type == "gte":  # >=
            if isinstance(val, (int, float)) and isinstance(filter_val, (int, float, str)):
                try:
                    return val >= float(filter_val)
                except:
                    pass
            # Fechas
            val_date = self._parse_date(val)
            filter_date = self._parse_date(filter_val)
            if val_date and filter_date:
                return val_date >= filter_date
            return str(val) >= str(filter_val)
        
        elif filter_type == "lte":  # <=
            if isinstance(val, (int, float)) and isinstance(filter_val, (int, float, str)):
                try:
                    return val <= float(filter_val)
                except:
                    pass
            val_date = self._parse_date(val)
            filter_date = self._parse_date(filter_val)
            if val_date and filter_date:
                return val_date <= filter_date
            return str(val) <= str(filter_val)
        
        elif filter_type == "contains":
            return str(filter_val).lower() in str(val).lower()
        
        return True
    
    def _eval_sum_equals(
        self, values: List, field_path: str, params: Dict, req: Dict
    ) -> Tuple[bool, List[RuleViolation]]:
        """Valida que la suma de valores sea igual a un valor esperado"""
        violations = []
        
        expected_sum = params.get("expected")
        tolerance = params.get("tolerance", 0.01)
        
        if expected_sum is None:
            return True, []
        
        numeric_values = [v for v in values if isinstance(v, (int, float))]
        actual_sum = sum(numeric_values)
        
        if abs(actual_sum - expected_sum) > tolerance:
            violations.append(RuleViolation(
                rule_type="sum_equals",
                field_path=field_path,
                message=f"Suma {actual_sum} no coincide con esperado {expected_sum}",
                actual_value=actual_sum,
                expected=expected_sum
            ))
        
        return len(violations) == 0, violations
    
    def _eval_sum_equals_field(
        self, values: List, field_path: str, params: Dict, req: Dict
    ) -> Tuple[bool, List[RuleViolation]]:
        """Valida que la suma de valores sea igual a otro campo en el response"""
        # Esta regla necesita acceso al data completo, se implementa en validator
        return True, []
    
    def _eval_monotonic_sequence(
        self, values: List, field_path: str, params: Dict, req: Dict
    ) -> Tuple[bool, List[RuleViolation]]:
        """Valida que valores sean secuencia monótona (creciente o decreciente)"""
        violations = []
        
        direction = params.get("direction", "increasing")  # increasing, decreasing
        
        if len(values) < 2:
            return True, []
        
        for i in range(1, len(values)):
            if direction == "increasing":
                if values[i] < values[i-1]:
                    violations.append(RuleViolation(
                        rule_type="monotonic_sequence",
                        field_path=field_path,
                        message=f"Secuencia no es creciente en posición {i}",
                        actual_value=f"{values[i-1]} -> {values[i]}",
                        expected="creciente"
                    ))
                    break
            else:
                if values[i] > values[i-1]:
                    violations.append(RuleViolation(
                        rule_type="monotonic_sequence",
                        field_path=field_path,
                        message=f"Secuencia no es decreciente en posición {i}",
                        actual_value=f"{values[i-1]} -> {values[i]}",
                        expected="decreciente"
                    ))
                    break
        
        return len(violations) == 0, violations
    
    def _eval_fields_present(
        self, values: List, field_path: str, params: Dict, req: Dict
    ) -> Tuple[bool, List[RuleViolation]]:
        """Valida que campos requeridos estén presentes en objetos"""
        violations = []
        
        required_fields = params.get("required", [])
        
        for obj in values:
            if not isinstance(obj, dict):
                continue
            
            for field in required_fields:
                if field not in obj:
                    violations.append(RuleViolation(
                        rule_type="fields_present",
                        field_path=f"{field_path}.{field}",
                        message=f"Campo requerido '{field}' no encontrado",
                        actual_value=list(obj.keys()),
                        expected=required_fields
                    ))
        
        return len(violations) == 0, violations
    
    def _eval_array_not_empty(
        self, values: List, field_path: str, params: Dict, req: Dict
    ) -> Tuple[bool, List[RuleViolation]]:
        """Valida que arrays no estén vacíos"""
        violations = []
        
        for val in values:
            if isinstance(val, list) and len(val) == 0:
                violations.append(RuleViolation(
                    rule_type="array_not_empty",
                    field_path=field_path,
                    message="Array vacío detectado",
                    actual_value=[],
                    expected="al menos 1 elemento"
                ))
        
        return len(violations) == 0, violations
    
    def _eval_unique_values(
        self, values: List, field_path: str, params: Dict, req: Dict
    ) -> Tuple[bool, List[RuleViolation]]:
        """Valida que no haya valores duplicados"""
        violations = []
        
        seen = {}
        for val in values:
            val_str = str(val)
            if val_str in seen:
                violations.append(RuleViolation(
                    rule_type="unique_values",
                    field_path=field_path,
                    message=f"Valor duplicado: {val}",
                    actual_value=val,
                    expected="valores únicos"
                ))
            seen[val_str] = True
        
        return len(violations) == 0, violations
    
    def _eval_no_credentials_in_output(
        self, values: List, field_path: str, params: Dict, req: Dict
    ) -> Tuple[bool, List[RuleViolation]]:
        """Valida que no haya credenciales en el output"""
        violations = []
        
        def check_object(obj: Any, path: str):
            if isinstance(obj, dict):
                for key, val in obj.items():
                    key_lower = key.lower()
                    for sensitive in SENSITIVE_FIELDS:
                        if sensitive in key_lower:
                            violations.append(RuleViolation(
                                rule_type="no_credentials_in_output",
                                field_path=f"{path}.{key}",
                                message=f"Campo sensible '{key}' detectado en output",
                                actual_value="[REDACTED]",
                                expected="campo no debería existir"
                            ))
                    check_object(val, f"{path}.{key}")
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    check_object(item, f"{path}[{i}]")
        
        for val in values:
            check_object(val, field_path)
        
        return len(violations) == 0, violations


# Lista de reglas disponibles para documentación
AVAILABLE_RULES = {
    "date_in_range": {
        "description": "Valida que fechas estén dentro de un rango",
        "params": ["min_date", "max_date", "days_back", "days_forward"],
        "example": {"rule_type": "date_in_range", "field_path": "$.items[*].fecha", "params": {"days_back": 365}}
    },
    "no_future_dates": {
        "description": "Valida que no haya fechas futuras",
        "params": ["tolerance_days"],
        "example": {"rule_type": "no_future_dates", "field_path": "$.fecha_registro"}
    },
    "allowed_values": {
        "description": "Valida que valores estén en lista permitida",
        "params": ["values"],
        "example": {"rule_type": "allowed_values", "field_path": "$.estado", "params": {"values": ["activo", "inactivo"]}}
    },
    "respects_filter": {
        "description": "Valida que resultados respeten filtro enviado en request",
        "params": ["filter_param", "filter_type"],
        "example": {"rule_type": "respects_filter", "field_path": "$.items[*].fecha", "params": {"filter_param": "fecha_desde", "filter_type": "gte"}}
    },
    "no_credentials_in_output": {
        "description": "Detecta campos sensibles (passwords, tokens) en output",
        "params": [],
        "example": {"rule_type": "no_credentials_in_output", "field_path": "$"}
    }
}
