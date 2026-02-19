"""
BUENOBOT v2.0 - Security Hardening Module

Funciones de seguridad adicionales para hardening del sistema.
Incluye sanitización de logs, redacción de campos sensibles,
y validación de inputs.
"""
import re
import logging
import hashlib
from typing import Any, Dict, List, Optional, Set
from datetime import datetime

logger = logging.getLogger(__name__)


# === CAMPOS SENSIBLES ===
SENSITIVE_FIELD_PATTERNS = [
    r'.*password.*',
    r'.*passwd.*',
    r'.*pwd.*',
    r'.*secret.*',
    r'.*token.*',
    r'.*api[_-]?key.*',
    r'.*auth.*',
    r'.*credential.*',
    r'.*private[_-]?key.*',
    r'.*ssh[_-]?key.*',
    r'.*bearer.*',
    r'.*session[_-]?id.*',
    r'.*cookie.*',
]

SENSITIVE_VALUE_PATTERNS = [
    r'eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*',  # JWT
    r'[a-fA-F0-9]{40}',  # SHA-1 (tokens)
    r'[a-fA-F0-9]{64}',  # SHA-256
    r'sk-[a-zA-Z0-9]{48}',  # OpenAI API keys
    r'ghp_[a-zA-Z0-9]{36}',  # GitHub tokens
    r'gho_[a-zA-Z0-9]{36}',  # GitHub OAuth tokens
]


class SecuritySanitizer:
    """
    Sanitizador de seguridad para logs y outputs.
    
    Uso:
        sanitizer = SecuritySanitizer()
        safe_dict = sanitizer.sanitize_dict(sensitive_dict)
        safe_log = sanitizer.sanitize_string(log_message)
    """
    
    def __init__(
        self,
        redaction_text: str = "***REDACTED***",
        additional_fields: Optional[List[str]] = None
    ):
        self.redaction_text = redaction_text
        self.sensitive_patterns = SENSITIVE_FIELD_PATTERNS.copy()
        
        if additional_fields:
            for field in additional_fields:
                self.sensitive_patterns.append(f".*{re.escape(field)}.*")
        
        self._compiled_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.sensitive_patterns
        ]
        self._value_patterns = [
            re.compile(p) for p in SENSITIVE_VALUE_PATTERNS
        ]
    
    def is_sensitive_field(self, field_name: str) -> bool:
        """Determina si un campo es sensible por su nombre"""
        return any(p.match(field_name) for p in self._compiled_patterns)
    
    def is_sensitive_value(self, value: str) -> bool:
        """Determina si un valor parece ser sensible (token, key, etc.)"""
        if len(value) < 10:
            return False
        return any(p.search(value) for p in self._value_patterns)
    
    def sanitize_value(self, value: Any, field_name: str = "") -> Any:
        """Sanitiza un valor individual"""
        if value is None:
            return None
        
        # Si el campo es sensible, redactar
        if field_name and self.is_sensitive_field(field_name):
            return self.redaction_text
        
        # Si es string, verificar patrones de valores sensibles
        if isinstance(value, str):
            if self.is_sensitive_value(value):
                return self.redaction_text
            return value
        
        # Recursión para estructuras complejas
        if isinstance(value, dict):
            return self.sanitize_dict(value)
        if isinstance(value, list):
            return [self.sanitize_value(v) for v in value]
        
        return value
    
    def sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitiza un diccionario removiendo/ocultando campos sensibles"""
        result = {}
        
        for key, value in data.items():
            if self.is_sensitive_field(key):
                result[key] = self.redaction_text
            elif isinstance(value, dict):
                result[key] = self.sanitize_dict(value)
            elif isinstance(value, list):
                result[key] = [self.sanitize_value(v, key) for v in value]
            elif isinstance(value, str) and self.is_sensitive_value(value):
                result[key] = self.redaction_text
            else:
                result[key] = value
        
        return result
    
    def sanitize_string(self, text: str) -> str:
        """Sanitiza un string removiendo valores sensibles"""
        result = text
        
        # Redactar patrones conocidos
        for pattern, replacement in [
            (r'password["\']?\s*[:=]\s*["\'][^"\']*["\']', f'password={self.redaction_text}'),
            (r'api[_-]?key["\']?\s*[:=]\s*["\'][^"\']*["\']', f'api_key={self.redaction_text}'),
            (r'token["\']?\s*[:=]\s*["\'][^"\']*["\']', f'token={self.redaction_text}'),
            (r'secret["\']?\s*[:=]\s*["\'][^"\']*["\']', f'secret={self.redaction_text}'),
            (r'authorization:\s*[^\n]+', f'Authorization: {self.redaction_text}'),
            (r'bearer\s+[a-zA-Z0-9._-]+', f'Bearer {self.redaction_text}'),
        ]:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        # Redactar valores que parecen tokens
        for pattern in self._value_patterns:
            result = pattern.sub(self.redaction_text, result)
        
        return result
    
    def sanitize_for_logging(self, data: Any) -> str:
        """Convierte datos a string sanitizado para logging"""
        if isinstance(data, dict):
            sanitized = self.sanitize_dict(data)
            return str(sanitized)
        elif isinstance(data, str):
            return self.sanitize_string(data)
        else:
            return str(data)


class InputValidator:
    """
    Validador de inputs para prevenir injection attacks.
    """
    
    # Patrones peligrosos en inputs
    DANGEROUS_PATTERNS = [
        r'[;\|&`$]',  # Shell metacaracteres
        r'\.\.',  # Path traversal
        r'<script',  # XSS
        r'javascript:',
        r'data:text/html',
        r'on\w+=',  # Event handlers XSS
    ]
    
    def __init__(self):
        self._dangerous_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.DANGEROUS_PATTERNS
        ]
    
    def is_safe_path(self, path: str, base_dir: str) -> bool:
        """Valida que un path sea seguro y esté dentro de base_dir"""
        import os
        
        # Normalizar
        try:
            if not path.startswith('/'):
                full_path = os.path.normpath(os.path.join(base_dir, path))
            else:
                full_path = os.path.normpath(path)
            
            base_normalized = os.path.normpath(base_dir)
            
            # Verificar que esté dentro de base_dir
            if not full_path.startswith(base_normalized):
                return False
            
            # Verificar que no contenga path traversal
            if '..' in path:
                return False
            
            return True
            
        except Exception:
            return False
    
    def is_safe_input(self, value: str) -> bool:
        """Verifica que un input no contenga patrones peligrosos"""
        return not any(p.search(value) for p in self._dangerous_patterns)
    
    def sanitize_for_shell(self, value: str) -> str:
        """Escapa un valor para uso seguro en shell (aunque preferimos evitarlo)"""
        import shlex
        return shlex.quote(value)
    
    def validate_scan_request(self, request: Dict[str, Any]) -> List[str]:
        """Valida request de scan y retorna lista de errores"""
        errors = []
        
        # Validar environment
        env = request.get('environment', '')
        if env not in ['dev', 'prod', 'staging', 'test']:
            errors.append(f"Environment inválido: {env}")
        
        # Validar checks si se especifican
        checks = request.get('checks', [])
        if checks:
            # Solo permitir nombres alfanuméricos con guiones/underscores
            for check in checks:
                if not re.match(r'^[a-zA-Z0-9_-]+$', check):
                    errors.append(f"Check name inválido: {check}")
        
        # Validar triggered_by (debería ser un username o email)
        triggered_by = request.get('triggered_by', '')
        if triggered_by and len(triggered_by) > 100:
            errors.append("triggered_by demasiado largo")
        
        return errors


class AuditLogger:
    """
    Logger de auditoría para tracking de acciones de seguridad.
    """
    
    def __init__(self, logger_name: str = "buenobot.audit"):
        self.logger = logging.getLogger(logger_name)
        self.sanitizer = SecuritySanitizer()
    
    def log_scan_start(
        self,
        scan_id: str,
        scan_type: str,
        environment: str,
        triggered_by: Optional[str] = None
    ):
        """Registra inicio de scan"""
        self.logger.info(
            f"SCAN_START | id={scan_id} | type={scan_type} | "
            f"env={environment} | user={triggered_by or 'system'}"
        )
    
    def log_scan_complete(
        self,
        scan_id: str,
        gate_status: str,
        duration_seconds: float,
        findings_count: int
    ):
        """Registra finalización de scan"""
        self.logger.info(
            f"SCAN_COMPLETE | id={scan_id} | gate={gate_status} | "
            f"duration={duration_seconds:.2f}s | findings={findings_count}"
        )
    
    def log_command_execution(
        self,
        command_name: str,
        success: bool,
        duration_ms: int,
        context: Optional[Dict] = None
    ):
        """Registra ejecución de comando"""
        ctx_safe = self.sanitizer.sanitize_dict(context) if context else {}
        self.logger.info(
            f"COMMAND_EXEC | cmd={command_name} | success={success} | "
            f"duration={duration_ms}ms | context={ctx_safe}"
        )
    
    def log_security_finding(
        self,
        finding_type: str,
        severity: str,
        location: str,
        description: str
    ):
        """Registra hallazgo de seguridad"""
        # Sanitizar descripción
        safe_desc = self.sanitizer.sanitize_string(description)[:200]
        self.logger.warning(
            f"SECURITY_FINDING | type={finding_type} | severity={severity} | "
            f"location={location} | desc={safe_desc}"
        )
    
    def log_access_denied(
        self,
        action: str,
        user: Optional[str] = None,
        reason: str = ""
    ):
        """Registra intento de acceso denegado"""
        self.logger.warning(
            f"ACCESS_DENIED | action={action} | user={user or 'unknown'} | reason={reason}"
        )


# === FUNCIONES DE UTILIDAD ===

def generate_finding_hash(finding_title: str, location: str) -> str:
    """Genera hash único para un finding (para deduplicación)"""
    content = f"{finding_title}:{location}"
    return hashlib.sha256(content.encode()).hexdigest()[:12]


def mask_sensitive_url(url: str) -> str:
    """Enmascara credenciales en URLs"""
    # Patrón: scheme://user:password@host
    pattern = r'(https?://)([^:]+):([^@]+)@'
    return re.sub(pattern, r'\1\2:***@', url)


def truncate_for_display(text: str, max_length: int = 200) -> str:
    """Trunca texto para display seguro"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


# Instancias singleton
_sanitizer: Optional[SecuritySanitizer] = None
_validator: Optional[InputValidator] = None
_audit_logger: Optional[AuditLogger] = None


def get_sanitizer() -> SecuritySanitizer:
    global _sanitizer
    if _sanitizer is None:
        _sanitizer = SecuritySanitizer()
    return _sanitizer


def get_validator() -> InputValidator:
    global _validator
    if _validator is None:
        _validator = InputValidator()
    return _validator


def get_audit_logger() -> AuditLogger:
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
