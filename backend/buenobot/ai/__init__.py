"""
BUENOBOT v3.0 - AI Module

Motor de IA híbrido para enriquecimiento de reportes.
Soporta motor local (Ollama/mock) y API (OpenAI).
"""

from .gateway import AIGateway, get_ai_gateway
from .router import AIRouter, EngineSelection
from .local_engine import LocalEngine
from .openai_engine import OpenAIEngine
from ..evidence import EvidencePack, EvidencePackBuilder, get_evidence_builder
from ..cache_ai import AICache, get_ai_cache

__all__ = [
    "AIGateway",
    "get_ai_gateway",
    "AIRouter",
    "EngineSelection",
    "LocalEngine",
    "OpenAIEngine",
    "EvidencePack",
    "EvidencePackBuilder",
    "get_evidence_builder",
    "AICache",
    "get_ai_cache",
]
