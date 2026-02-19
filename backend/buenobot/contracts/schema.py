"""
BUENOBOT v2.0 - Contract Schema

Define la estructura de contratos YAML para validación de outputs.
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from enum import Enum
from pathlib import Path
import yaml
import logging

logger = logging.getLogger(__name__)


class RuleType(str, Enum):
    """Tipos de reglas de validación disponibles"""
    # Validaciones de fecha
    DATE_IN_RANGE = "date_in_range"
    NO_FUTURE_DATES = "no_future_dates"
    
    # Validaciones de valores
    ALLOWED_VALUES = "allowed_values"
    ALLOWED_VALUES_IF = "allowed_values_if"  # Condicional
    NOT_NULL = "not_null"
    NO_NEGATIVE_VALUES = "no_negative_values"
    
    # Validaciones de filtros
    SUBSET_OF_PARAM = "subset_of_param"  # Valores deben estar en param enviado
    RESPECTS_FILTER = "respects_filter"   # Si filtro X enviado, todos los items lo cumplen
    
    # Validaciones numéricas
    SUM_EQUALS = "sum_equals"
    SUM_EQUALS_FIELD = "sum_equals_field"
    MONOTONIC_SEQUENCE = "monotonic_sequence"
    
    # Validaciones de estructura
    FIELDS_PRESENT = "fields_present"
    ARRAY_NOT_EMPTY = "array_not_empty"
    UNIQUE_VALUES = "unique_values"
    
    # Validaciones de seguridad
    NO_CREDENTIALS_IN_OUTPUT = "no_credentials_in_output"


class ContractRule(BaseModel):
    """Una regla individual de validación"""
    rule_type: RuleType
    field_path: str = Field(description="JSONPath al campo a validar (e.g., '$.items[*].fecha')")
    params: Dict[str, Any] = Field(default_factory=dict, description="Parámetros de la regla")
    severity: str = Field(default="high", description="critical|high|medium|low")
    message: Optional[str] = None  # Mensaje personalizado de error
    enabled: bool = True
    
    class Config:
        use_enum_values = True


class EndpointContract(BaseModel):
    """Contrato de validación para un endpoint específico"""
    endpoint: str = Field(description="Ruta del endpoint (e.g., /api/v1/stock/camaras)")
    method: str = Field(default="GET", description="HTTP method")
    description: str = ""
    version: str = "1.0"
    
    # Validaciones del output
    rules: List[ContractRule] = []
    
    # Condiciones de aplicación
    response_codes: List[int] = Field(default=[200], description="Códigos HTTP donde aplica")
    content_type: str = Field(default="application/json")
    
    # Filter validation rules - validar que filtros enviados se respeten
    filter_validations: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Validaciones de que filtros de request se reflejen en response"
    )
    
    class Config:
        use_enum_values = True


class ContractRegistry:
    """
    Registro central de contratos.
    Carga contratos desde archivos YAML y los indexa por endpoint.
    """
    
    def __init__(self, contracts_dir: Optional[str] = None):
        self.contracts_dir = contracts_dir or "/app/backend/buenobot/contracts/definitions"
        self._contracts: Dict[str, EndpointContract] = {}
        self._loaded = False
    
    def _make_key(self, endpoint: str, method: str = "GET") -> str:
        """Genera clave única para endpoint"""
        return f"{method.upper()}:{endpoint}"
    
    def load_contracts(self, reload: bool = False) -> int:
        """
        Carga todos los contratos desde YAML.
        Returns: Número de contratos cargados.
        """
        if self._loaded and not reload:
            return len(self._contracts)
        
        self._contracts.clear()
        contracts_path = Path(self.contracts_dir)
        
        if not contracts_path.exists():
            logger.warning(f"Directorio de contratos no existe: {contracts_path}")
            return 0
        
        loaded = 0
        for yaml_file in contracts_path.glob("*.yaml"):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                
                if not data:
                    continue
                
                # Un archivo puede tener múltiples contratos
                contracts_list = data.get('contracts', [data])
                if not isinstance(contracts_list, list):
                    contracts_list = [contracts_list]
                
                for contract_data in contracts_list:
                    try:
                        contract = EndpointContract(**contract_data)
                        key = self._make_key(contract.endpoint, contract.method)
                        self._contracts[key] = contract
                        loaded += 1
                        logger.debug(f"Contrato cargado: {key}")
                    except Exception as e:
                        logger.error(f"Error parseando contrato en {yaml_file}: {e}")
                        
            except Exception as e:
                logger.error(f"Error cargando {yaml_file}: {e}")
        
        self._loaded = True
        logger.info(f"Cargados {loaded} contratos de {contracts_path}")
        return loaded
    
    def get_contract(self, endpoint: str, method: str = "GET") -> Optional[EndpointContract]:
        """Obtiene contrato para un endpoint específico"""
        if not self._loaded:
            self.load_contracts()
        
        key = self._make_key(endpoint, method)
        return self._contracts.get(key)
    
    def get_all_contracts(self) -> Dict[str, EndpointContract]:
        """Retorna todos los contratos cargados"""
        if not self._loaded:
            self.load_contracts()
        return self._contracts.copy()
    
    def register_contract(self, contract: EndpointContract) -> None:
        """Registra un contrato programáticamente"""
        key = self._make_key(contract.endpoint, contract.method)
        self._contracts[key] = contract
    
    def has_contract(self, endpoint: str, method: str = "GET") -> bool:
        """Verifica si existe contrato para endpoint"""
        if not self._loaded:
            self.load_contracts()
        key = self._make_key(endpoint, method)
        return key in self._contracts


# Singleton global
_registry: Optional[ContractRegistry] = None


def get_contract_registry() -> ContractRegistry:
    """Obtiene instancia singleton del registry"""
    global _registry
    if _registry is None:
        _registry = ContractRegistry()
    return _registry
