"""
BUENOBOT v2.0 - Output Contract System

Sistema de validación de contratos de salida para endpoints API.
Define reglas YAML para validar respuestas de endpoints.
"""
from .schema import ContractRule, EndpointContract, ContractRegistry, get_contract_registry
from .validator import ContractValidator
from .rules import AVAILABLE_RULES, RuleEvaluator

__all__ = [
    "ContractRule",
    "EndpointContract", 
    "ContractRegistry",
    "get_contract_registry",
    "ContractValidator",
    "AVAILABLE_RULES",
    "RuleEvaluator"
]
