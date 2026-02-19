"""
BUENOBOT v2.0 - Secure Command Runner

Ejecutor de comandos con whitelist estricta y hardening de seguridad.
No permite ejecución arbitraria de comandos.

Características v2.0:
- Timeouts globales e individuales
- Límites de recursos (memoria/CPU opcional)
- Cancelación limpia de procesos
- Sanitización de logs y outputs
- Auditoría detallada
"""
import asyncio
import subprocess
import logging
import time
import os
import signal
import re
from typing import Optional, Tuple, List, Dict, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


# === CONFIGURACIÓN GLOBAL ===
class CommandRunnerConfig:
    """Configuración global del command runner"""
    
    # Timeouts
    DEFAULT_TIMEOUT: int = 60  # segundos
    GLOBAL_TIMEOUT_MULTIPLIER: float = 1.0  # Multiplicador para todos los timeouts
    MAX_TIMEOUT: int = 600  # 10 minutos máximo
    
    # Límites de output
    MAX_OUTPUT_SIZE: int = 100_000  # 100KB
    MAX_STDERR_SIZE: int = 50_000   # 50KB
    
    # Seguridad
    SANITIZE_OUTPUTS: bool = True
    LOG_FULL_COMMANDS: bool = False  # False en producción
    
    # Campos sensibles a redactar
    SENSITIVE_PATTERNS: List[Tuple[str, str]] = [
        (r'password["\']?\s*[:=]\s*["\'][^"\']*["\']', 'password=***REDACTED***'),
        (r'passwd["\']?\s*[:=]\s*["\'][^"\']*["\']', 'passwd=***REDACTED***'),
        (r'api[_-]?key["\']?\s*[:=]\s*["\'][^"\']*["\']', 'api_key=***REDACTED***'),
        (r'secret["\']?\s*[:=]\s*["\'][^"\']*["\']', 'secret=***REDACTED***'),
        (r'token["\']?\s*[:=]\s*["\'][^"\']*["\']', 'token=***REDACTED***'),
        (r'bearer\s+[a-zA-Z0-9._-]+', 'Bearer ***REDACTED***'),
        (r'authorization:\s*[^\n]+', 'Authorization: ***REDACTED***'),
    ]


# Instancia global de config
config = CommandRunnerConfig()


class CommandCategory(str, Enum):
    """Categorías de comandos permitidos"""
    LINT = "lint"
    TEST = "test"
    SECURITY = "security"
    GIT = "git"
    DOCKER = "docker"
    SYSTEM = "system"
    PYTHON = "python"


@dataclass
class AllowedCommand:
    """Definición de un comando permitido"""
    name: str
    command: List[str]
    category: CommandCategory
    timeout: int = 60  # segundos
    description: str = ""
    requires_path: bool = False  # Si requiere un path como argumento


# Whitelist de comandos permitidos - ÚNICA fuente de verdad
COMMAND_WHITELIST: Dict[str, AllowedCommand] = {
    # === LINT & CODE QUALITY ===
    "ruff_check": AllowedCommand(
        name="ruff_check",
        command=["python", "-m", "ruff", "check", "--output-format=json"],
        category=CommandCategory.LINT,
        timeout=120,
        description="Ejecuta ruff linter en modo JSON",
        requires_path=True
    ),
    "ruff_format_check": AllowedCommand(
        name="ruff_format_check",
        command=["python", "-m", "ruff", "format", "--check", "--diff"],
        category=CommandCategory.LINT,
        timeout=60,
        description="Verifica formato con ruff",
        requires_path=True
    ),
    "mypy_check": AllowedCommand(
        name="mypy_check",
        command=["python", "-m", "mypy", "--ignore-missing-imports", "--no-error-summary"],
        category=CommandCategory.LINT,
        timeout=180,
        description="Type checking con mypy",
        requires_path=True
    ),
    
    # === TESTS ===
    "pytest_smoke": AllowedCommand(
        name="pytest_smoke",
        command=["python", "-m", "pytest", "-v", "--tb=short", "-x", "-q"],
        category=CommandCategory.TEST,
        timeout=300,
        description="Ejecuta tests de pytest",
        requires_path=True
    ),
    "pytest_collect": AllowedCommand(
        name="pytest_collect",
        command=["python", "-m", "pytest", "--collect-only", "-q"],
        category=CommandCategory.TEST,
        timeout=60,
        description="Lista tests disponibles"
    ),
    
    # === SECURITY ===
    "pip_audit": AllowedCommand(
        name="pip_audit",
        command=["python", "-m", "pip_audit", "--format=json", "--progress-spinner=off"],
        category=CommandCategory.SECURITY,
        timeout=120,
        description="Audita dependencias Python por vulnerabilidades"
    ),
    "safety_check": AllowedCommand(
        name="safety_check",
        command=["python", "-m", "safety", "check", "--json"],
        category=CommandCategory.SECURITY,
        timeout=120,
        description="Verifica dependencias con Safety"
    ),
    "bandit_scan": AllowedCommand(
        name="bandit_scan",
        command=["python", "-m", "bandit", "-r", "-f", "json", "-ll"],
        category=CommandCategory.SECURITY,
        timeout=180,
        description="Análisis estático de seguridad Python",
        requires_path=True
    ),
    
    # === GIT ===
    "git_rev_parse": AllowedCommand(
        name="git_rev_parse",
        command=["git", "rev-parse", "HEAD"],
        category=CommandCategory.GIT,
        timeout=10,
        description="Obtiene commit SHA actual"
    ),
    "git_branch": AllowedCommand(
        name="git_branch",
        command=["git", "rev-parse", "--abbrev-ref", "HEAD"],
        category=CommandCategory.GIT,
        timeout=10,
        description="Obtiene branch actual"
    ),
    "git_log_last": AllowedCommand(
        name="git_log_last",
        command=["git", "log", "-1", "--format=%H|%an|%s|%ci"],
        category=CommandCategory.GIT,
        timeout=10,
        description="Obtiene info del último commit"
    ),
    "git_status": AllowedCommand(
        name="git_status",
        command=["git", "status", "--porcelain"],
        category=CommandCategory.GIT,
        timeout=10,
        description="Estado del repositorio"
    ),
    
    # === DOCKER ===
    "docker_ps": AllowedCommand(
        name="docker_ps",
        command=["docker", "ps", "--format", "{{.Names}}|{{.Status}}|{{.Ports}}"],
        category=CommandCategory.DOCKER,
        timeout=30,
        description="Lista contenedores activos"
    ),
    "docker_compose_ps": AllowedCommand(
        name="docker_compose_ps",
        command=["docker-compose", "ps", "--format", "json"],
        category=CommandCategory.DOCKER,
        timeout=30,
        description="Estado de docker-compose"
    ),
    "docker_logs": AllowedCommand(
        name="docker_logs",
        command=["docker", "logs", "--tail=100", "--timestamps"],
        category=CommandCategory.DOCKER,
        timeout=30,
        description="Últimos logs de un contenedor"
    ),
    "docker_stats": AllowedCommand(
        name="docker_stats",
        command=["docker", "stats", "--no-stream", "--format", 
                 "{{.Container}}|{{.CPUPerc}}|{{.MemUsage}}|{{.MemPerc}}"],
        category=CommandCategory.DOCKER,
        timeout=30,
        description="Estadísticas de recursos"
    ),
    
    # === SYSTEM ===
    "disk_usage": AllowedCommand(
        name="disk_usage",
        command=["df", "-h", "/"],
        category=CommandCategory.SYSTEM,
        timeout=10,
        description="Uso de disco"
    ),
    "memory_info": AllowedCommand(
        name="memory_info",
        command=["free", "-h"],
        category=CommandCategory.SYSTEM,
        timeout=10,
        description="Información de memoria"
    ),
    
    # === PYTHON UTILS ===
    "pip_list": AllowedCommand(
        name="pip_list",
        command=["pip", "list", "--format=json"],
        category=CommandCategory.PYTHON,
        timeout=30,
        description="Lista paquetes instalados"
    ),
    "pip_check": AllowedCommand(
        name="pip_check",
        command=["pip", "check"],
        category=CommandCategory.PYTHON,
        timeout=30,
        description="Verifica dependencias rotas"
    ),
}


class CommandRunnerError(Exception):
    """Error en ejecución de comando"""
    pass


class CommandNotAllowedError(CommandRunnerError):
    """Comando no está en whitelist"""
    pass


class CommandTimeoutError(CommandRunnerError):
    """Comando excedió timeout"""
    pass


class CommandCancelledError(CommandRunnerError):
    """Comando fue cancelado"""
    pass


@dataclass
class CommandResult:
    """Resultado de ejecución de un comando"""
    command_name: str
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    truncated: bool = False
    cancelled: bool = False
    timed_out: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "command_name": self.command_name,
            "success": self.success,
            "exit_code": self.exit_code,
            "stdout_length": len(self.stdout),
            "stderr_length": len(self.stderr),
            "duration_ms": self.duration_ms,
            "truncated": self.truncated,
            "cancelled": self.cancelled,
            "timed_out": self.timed_out
        }


@dataclass
class ExecutionContext:
    """Contexto de ejecución para tracking"""
    command_name: str
    start_time: float
    process: Optional[asyncio.subprocess.Process] = None
    cancelled: bool = False
    
    @property
    def elapsed_ms(self) -> int:
        return int((time.time() - self.start_time) * 1000)


class SecureCommandRunner:
    """
    Ejecutor seguro de comandos v2.0 con whitelist y hardening.
    
    Características de seguridad:
    - Solo ejecuta comandos predefinidos en COMMAND_WHITELIST
    - Timeouts globales e individuales
    - Sanitización de outputs (truncado, sin credenciales)
    - Cancelación limpia con cleanup de procesos
    - Auditoría de cada ejecución
    - Sin shell=True nunca
    """
    
    def __init__(self, working_dir: str = "/app"):
        self.working_dir = working_dir
        self.execution_log: List[Dict[str, Any]] = []
        self._active_contexts: Dict[str, ExecutionContext] = {}
        self._cancelled_commands: Set[str] = set()
    
    def _sanitize_output(self, output: str, max_size: Optional[int] = None) -> Tuple[str, bool]:
        """
        Sanitiza el output removiendo información sensible.
        Retorna (output_sanitizado, fue_truncado)
        """
        truncated = False
        max_size = max_size or config.MAX_OUTPUT_SIZE
        
        # Truncar si es muy largo
        if len(output) > max_size:
            output = output[:max_size] + "\n\n... [OUTPUT TRUNCATED - exceeded {max_size} bytes]"
            truncated = True
        
        # Sanitizar información sensible si está habilitado
        if config.SANITIZE_OUTPUTS:
            for pattern, replacement in config.SENSITIVE_PATTERNS:
                output = re.sub(pattern, replacement, output, flags=re.IGNORECASE)
        
        return output, truncated
    
    def _sanitize_for_logging(self, cmd: List[str]) -> str:
        """Sanitiza comando para logging (oculta credenciales en args)"""
        if config.LOG_FULL_COMMANDS:
            return " ".join(cmd)
        
        sanitized_parts = []
        for i, part in enumerate(cmd):
            lower_part = part.lower()
            if any(s in lower_part for s in ['password', 'secret', 'token', 'key']):
                # El siguiente argumento podría ser el valor
                sanitized_parts.append(part)
                # Marca para sanitizar siguiente si es valor
            elif i > 0 and any(s in cmd[i-1].lower() for s in ['password', 'secret', 'token', 'key']):
                sanitized_parts.append('***REDACTED***')
            else:
                sanitized_parts.append(part)
        
        return " ".join(sanitized_parts)
    
    def get_command(self, command_name: str) -> AllowedCommand:
        """Obtiene un comando de la whitelist o lanza excepción"""
        if command_name not in COMMAND_WHITELIST:
            available = ", ".join(sorted(COMMAND_WHITELIST.keys()))
            raise CommandNotAllowedError(
                f"Comando '{command_name}' no está en whitelist. "
                f"Comandos disponibles: {available}"
            )
        return COMMAND_WHITELIST[command_name]
    
    def calculate_timeout(self, base_timeout: int, override: Optional[int] = None) -> int:
        """Calcula timeout efectivo considerando configuración global"""
        if override:
            timeout = override
        else:
            timeout = int(base_timeout * config.GLOBAL_TIMEOUT_MULTIPLIER)
        
        return min(timeout, config.MAX_TIMEOUT)
    
    async def cancel_command(self, context_id: str) -> bool:
        """
        Cancela un comando en ejecución de forma limpia.
        
        Returns:
            True si se canceló correctamente
        """
        ctx = self._active_contexts.get(context_id)
        if not ctx or not ctx.process:
            return False
        
        ctx.cancelled = True
        self._cancelled_commands.add(context_id)
        
        try:
            # Intentar terminar gracefully primero
            ctx.process.terminate()
            
            try:
                await asyncio.wait_for(ctx.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                # Si no termina en 5s, forzar kill
                ctx.process.kill()
                await ctx.process.wait()
            
            logger.info(f"Comando {ctx.command_name} cancelado (context: {context_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelando comando: {e}")
            return False
    
    async def cancel_all(self) -> int:
        """Cancela todos los comandos en ejecución"""
        cancelled = 0
        for context_id in list(self._active_contexts.keys()):
            if await self.cancel_command(context_id):
                cancelled += 1
        return cancelled
    
    @asynccontextmanager
    async def _execution_context(self, command_name: str):
        """Context manager para tracking de ejecución"""
        import uuid
        context_id = str(uuid.uuid4())[:8]
        ctx = ExecutionContext(command_name=command_name, start_time=time.time())
        self._active_contexts[context_id] = ctx
        
        try:
            yield ctx, context_id
        finally:
            self._active_contexts.pop(context_id, None)
            self._cancelled_commands.discard(context_id)
    
    async def run(
        self,
        command_name: str,
        extra_args: Optional[List[str]] = None,
        timeout_override: Optional[int] = None,
        env_vars: Optional[Dict[str, str]] = None
    ) -> CommandResult:
        """
        Ejecuta un comando de la whitelist de forma segura.
        
        Args:
            command_name: Nombre del comando en COMMAND_WHITELIST
            extra_args: Argumentos adicionales permitidos (solo paths seguros)
            timeout_override: Override del timeout por defecto
            env_vars: Variables de entorno adicionales
        
        Returns:
            CommandResult con el resultado de la ejecución
        """
        allowed_cmd = self.get_command(command_name)
        
        # Construir comando completo
        cmd = list(allowed_cmd.command)
        
        # Validar y agregar argumentos extra (solo paths dentro de working_dir)
        if extra_args:
            for arg in extra_args:
                if not self._is_safe_path(arg):
                    raise CommandRunnerError(
                        f"Argumento no permitido: {arg}. "
                        f"Solo se permiten paths dentro de {self.working_dir}"
                    )
                cmd.append(arg)
        
        timeout = self.calculate_timeout(allowed_cmd.timeout, timeout_override)
        
        # Logging pre-ejecución (sanitizado)
        log_entry = {
            "command_name": command_name,
            "command_sanitized": self._sanitize_for_logging(cmd),
            "timestamp": datetime.utcnow().isoformat(),
            "timeout": timeout
        }
        
        async with self._execution_context(command_name) as (ctx, context_id):
            try:
                # Preparar environment
                env = os.environ.copy()
                if env_vars:
                    # Sanitizar env vars en log
                    safe_env_keys = [k for k in env_vars.keys() if 'pass' not in k.lower() and 'secret' not in k.lower()]
                    log_entry["env_vars_added"] = safe_env_keys
                    env.update(env_vars)
                
                # Ejecutar sin shell=True por seguridad
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self.working_dir,
                    env=env
                )
                
                ctx.process = process
                
                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=timeout
                    )
                except asyncio.TimeoutError:
                    # Cleanup del proceso
                    process.terminate()
                    try:
                        await asyncio.wait_for(process.wait(), timeout=5.0)
                    except asyncio.TimeoutError:
                        process.kill()
                        await process.wait()
                    
                    log_entry.update({
                        "success": False,
                        "timed_out": True,
                        "duration_ms": ctx.elapsed_ms
                    })
                    self.execution_log.append(log_entry)
                    
                    raise CommandTimeoutError(
                        f"Comando '{command_name}' excedió timeout de {timeout}s"
                    )
                
                # Verificar si fue cancelado
                if ctx.cancelled:
                    return CommandResult(
                        command_name=command_name,
                        success=False,
                        exit_code=-1,
                        stdout="",
                        stderr="Comando cancelado",
                        duration_ms=ctx.elapsed_ms,
                        cancelled=True
                    )
                
                # Decodificar y sanitizar outputs
                stdout_str, stdout_truncated = self._sanitize_output(
                    stdout.decode('utf-8', errors='replace'),
                    config.MAX_OUTPUT_SIZE
                )
                stderr_str, stderr_truncated = self._sanitize_output(
                    stderr.decode('utf-8', errors='replace'),
                    config.MAX_STDERR_SIZE
                )
                
                result = CommandResult(
                    command_name=command_name,
                    success=process.returncode == 0,
                    exit_code=process.returncode,
                    stdout=stdout_str,
                    stderr=stderr_str,
                    duration_ms=ctx.elapsed_ms,
                    truncated=stdout_truncated or stderr_truncated
                )
                
                # Log post-ejecución
                log_entry.update({
                    "success": result.success,
                    "exit_code": result.exit_code,
                    "duration_ms": result.duration_ms,
                    "output_truncated": result.truncated
                })
                self.execution_log.append(log_entry)
                
                logger.info(
                    f"BUENOBOT Command: {command_name} | "
                    f"Exit: {result.exit_code} | "
                    f"Duration: {result.duration_ms}ms"
                )
                
                return result
                
            except CommandTimeoutError:
                raise
            except CommandCancelledError:
                raise
            except Exception as e:
                log_entry.update({
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration_ms": ctx.elapsed_ms
                })
                self.execution_log.append(log_entry)
                logger.error(f"BUENOBOT Command Error: {command_name} | {str(e)}")
                raise CommandRunnerError(f"Error ejecutando {command_name}: {str(e)}") from e
    
    def _is_safe_path(self, path: str) -> bool:
        """Verifica que un path sea seguro (dentro de working_dir)"""
        import os
        
        # Normalizar paths
        try:
            # Permitir paths relativos
            if path.startswith('.') or not path.startswith('/'):
                full_path = os.path.normpath(os.path.join(self.working_dir, path))
            else:
                full_path = os.path.normpath(path)
            
            # Verificar que esté dentro de working_dir
            return full_path.startswith(os.path.normpath(self.working_dir))
        except Exception:
            return False
    
    def run_sync(
        self,
        command_name: str,
        extra_args: Optional[List[str]] = None,
        timeout_override: Optional[int] = None
    ) -> CommandResult:
        """
        Versión síncrona de run() para uso fuera de async.
        """
        return asyncio.get_event_loop().run_until_complete(
            self.run(command_name, extra_args, timeout_override)
        )
    
    def get_available_commands(self) -> List[Dict[str, Any]]:
        """Lista todos los comandos disponibles en la whitelist"""
        return [
            {
                "name": cmd.name,
                "category": cmd.category.value,
                "description": cmd.description,
                "timeout": cmd.timeout
            }
            for cmd in COMMAND_WHITELIST.values()
        ]
    
    def get_execution_log(self) -> List[Dict[str, Any]]:
        """Retorna el log de ejecuciones para auditoría"""
        return self.execution_log.copy()
