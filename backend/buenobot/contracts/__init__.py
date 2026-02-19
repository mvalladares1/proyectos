"""
BUENOBOT v2.0 - Output Contract System

Sistema de validación de contratos de salida para endpoints API.
Define reglas YAML para validar respuestas de endpoints.
"""
from .schema import ContractRule, EndpointContract, ContractRegistry
from .validator import ContractValidator
from .rules import AVAILABLE_RULES, RuleEvaluator

__all__ = [
    "ContractRule",
    "EndpointContract", 
    "ContractRegistry",
    "ContractValidator",
    "AVAILABLE_RULES",
    "RuleEvaluator"
]
