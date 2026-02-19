"""
BUENOBOT v3.0 - AI Configuration

Settings para integración IA híbrida (Local + API).
Todas las configuraciones sensibles vía env vars.
"""
import os
from typing import Optional, Literal
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class AIEngineConfig(BaseSettings):
    """Configuración de motores de IA"""
    
    # === GENERAL ===
    ai_enabled: bool = Field(
        default=False,
        description="Habilitar integración IA globalmente"
    )
    
    default_engine: Literal["local", "openai", "mock"] = Field(
        default="mock",
        description="Motor por defecto: local, openai, mock"
    )
    
    analysis_mode: Literal["basic", "deep"] = Field(
        default="basic",
        description="Modo de análisis: basic (local) o deep (API)"
    )
    
    # === LOCAL ENGINE ===
    local_engine_mode: Literal["mock", "http"] = Field(
        default="mock",
        description="Modo del motor local: mock (dev) o http (ollama/etc)"
    )
    
    local_engine_url: str = Field(
        default="http://localhost:11434",
        description="URL del endpoint local LLM (ej: Ollama)"
    )
    
    local_engine_model: str = Field(
        default="llama2",
        description="Modelo a usar en motor local"
    )
    
    local_engine_timeout: int = Field(
        default=120,
        description="Timeout en segundos para motor local"
    )
    
    # === OPENAI ENGINE ===
    openai_api_key: Optional[str] = Field(
        default=None,
        description="API Key de OpenAI (env: OPENAI_API_KEY)"
    )
    
    openai_model: str = Field(
        default="gpt-4o-mini",
        description="Modelo OpenAI a usar"
    )
    
    openai_timeout: int = Field(
        default=60,
        description="Timeout en segundos para OpenAI API"
    )
    
    openai_max_tokens: int = Field(
        default=2000,
        description="Máximo de tokens en respuesta"
    )
    
    # === ROUTING LOGIC ===
    use_api_for_critical: bool = Field(
        default=True,
        description="Usar API para findings HIGH/CRITICAL"
    )
    
    use_api_for_complex: bool = Field(
        default=True,
        description="Usar API para triggers de complejidad"
    )
    
    complexity_triggers: list = Field(
        default=[
            "sql_injection_risk",
            "filter_leak_suspected",
            "contradictory_contracts",
            "multiple_critical_findings"
        ],
        description="Triggers que activan análisis profundo"
    )
    
    # === CACHE ===
    cache_enabled: bool = Field(
        default=True,
        description="Cachear resultados IA por commit_sha"
    )
    
    cache_ttl_hours: int = Field(
        default=24,
        description="TTL del cache en horas"
    )
    
    cache_dir: str = Field(
        default="/app/data/buenobot/ai_cache",
        description="Directorio para cache de IA"
    )
    
    # === LIMITS ===
    max_findings_to_ai: int = Field(
        default=25,
        description="Máximo de findings a enviar a IA"
    )
    
    max_evidence_tokens: int = Field(
        default=8000,
        description="Máximo de tokens en EvidencePack para IA"
    )
    
    max_log_lines: int = Field(
        default=100,
        description="Máximo de líneas de log a incluir"
    )
    
    # === SECURITY ===
    sanitize_evidence: bool = Field(
        default=True,
        description="Sanitizar evidencia antes de enviar a IA"
    )
    
    redact_patterns: list = Field(
        default=[
            r"password['\"]?\s*[:=]",
            r"api[_-]?key['\"]?\s*[:=]",
            r"token['\"]?\s*[:=]",
            r"secret['\"]?\s*[:=]",
            r"bearer\s+[a-zA-Z0-9._-]+",
        ],
        description="Patrones a redactar en evidencia"
    )
    
    class Config:
        env_prefix = "BUENOBOT_"
        env_file = ".env"
        extra = "ignore"


class PromptConfig(BaseModel):
    """Configuración de prompts"""
    
    # Límites de contexto
    max_findings_summary: int = 10
    max_code_snippets: int = 5
    max_contract_violations: int = 10
    
    # Templates
    system_prompt: str = """You are BUENOBOT, an AI security and quality analyst for the Rio Futuro Dashboards project.
Your role is to analyze scan results and provide actionable insights.

IMPORTANT RULES:
1. Never hallucinate - only cite evidence from the provided EvidencePack
2. Always reference finding IDs when making claims
3. Be concise and actionable
4. Output valid JSON only
5. Do not suggest running commands or directly accessing systems
6. The PASS/WARN/FAIL gate decision is already made deterministically - you only explain and suggest fixes"""


# === SINGLETON CONFIG ===
_config: Optional[AIEngineConfig] = None


def get_ai_config() -> AIEngineConfig:
    """Obtiene configuración AI (singleton)"""
    global _config
    if _config is None:
        _config = AIEngineConfig(
            ai_enabled=os.getenv("BUENOBOT_AI_ENABLED", "false").lower() == "true",
            default_engine=os.getenv("BUENOBOT_DEFAULT_ENGINE", "mock"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            local_engine_url=os.getenv("BUENOBOT_LOCAL_ENGINE_URL", "http://localhost:11434"),
            local_engine_mode=os.getenv("BUENOBOT_LOCAL_ENGINE_MODE", "mock"),
        )
    return _config


def reload_config() -> AIEngineConfig:
    """Recarga configuración desde env vars"""
    global _config
    _config = None
    return get_ai_config()


def update_ai_config(
    ai_enabled: Optional[bool] = None,
    openai_api_key: Optional[str] = None,
    openai_model: Optional[str] = None,
    default_engine: Optional[str] = None,
    cache_enabled: Optional[bool] = None
) -> AIEngineConfig:
    """Actualiza configuración AI en runtime (no persiste tras restart)"""
    global _config
    
    if _config is None:
        get_ai_config()
    
    # Crear dict con valores actuales
    current = _config.model_dump()
    
    # Actualizar solo los valores proporcionados
    if ai_enabled is not None:
        current["ai_enabled"] = ai_enabled
    if openai_api_key is not None:
        current["openai_api_key"] = openai_api_key
    if openai_model is not None:
        current["openai_model"] = openai_model
    if default_engine is not None:
        current["default_engine"] = default_engine
    if cache_enabled is not None:
        current["cache_enabled"] = cache_enabled
    
    # Crear nueva instancia con valores actualizados
    _config = AIEngineConfig(**current)
    
    return _config
