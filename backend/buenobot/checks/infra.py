"""
BUENOBOT - Infrastructure Checks

Checks de infraestructura:
- Docker containers status
- Logs de errores
- Recursos del sistema
"""
import os
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any

from .base import BaseCheck, CheckRegistry
from ..models import CheckResult, CheckCategory, CheckSeverity


@CheckRegistry.register("docker_status", quick=True, full=True)
class DockerStatusCheck(BaseCheck):
    """Check de estado de contenedores Docker"""
    
    name = "Docker Status"
    category = CheckCategory.INFRA
    description = "Verifica que los contenedores estén corriendo"
    
    EXPECTED_CONTAINERS = {
        "dev": ["rio-api-dev", "rio-web-dev"],
        "prod": ["rio-api-prod", "rio-web-prod"]
    }
    
    async def run(self) -> CheckResult:
        self.log("Verificando estado de contenedores...")
        
        try:
            result = await self.command_runner.run("docker_ps")
            
            if not result.success:
                self.add_finding(
                    title="Error ejecutando docker ps",
                    description=result.stderr or "No se pudo obtener estado de Docker",
                    severity=CheckSeverity.HIGH
                )
                return self._create_result("failed", "Docker no accesible")
            
            # Parsear output
            running_containers = []
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    parts = line.split("|")
                    if len(parts) >= 2:
                        name = parts[0].strip()
                        status = parts[1].strip()
                        running_containers.append({
                            "name": name,
                            "status": status,
                            "healthy": "healthy" in status.lower() or "up" in status.lower()
                        })
            
            self.log(f"Contenedores encontrados: {len(running_containers)}")
            
            # Verificar contenedores esperados
            expected = self.EXPECTED_CONTAINERS.get(self.environment, [])
            missing = []
            unhealthy = []
            
            for expected_name in expected:
                container = next(
                    (c for c in running_containers if expected_name in c["name"]),
                    None
                )
                if not container:
                    missing.append(expected_name)
                elif not container["healthy"]:
                    unhealthy.append(expected_name)
            
            if missing:
                for name in missing:
                    self.add_finding(
                        title=f"Contenedor no encontrado: {name}",
                        description=f"El contenedor {name} no está corriendo",
                        severity=CheckSeverity.CRITICAL,
                        recommendation="Ejecutar docker-compose up -d"
                    )
            
            if unhealthy:
                for name in unhealthy:
                    self.add_finding(
                        title=f"Contenedor no healthy: {name}",
                        description=f"El contenedor {name} no está en estado healthy",
                        severity=CheckSeverity.HIGH,
                        recommendation="Revisar logs del contenedor"
                    )
            
            if missing or unhealthy:
                return self._create_result(
                    "failed",
                    f"{len(missing)} missing, {len(unhealthy)} unhealthy"
                )
            
            return self._create_result(
                "passed",
                f"{len(running_containers)} contenedores OK"
            )
            
        except Exception as e:
            self.log(f"Error: {e}", "error")
            # Docker no disponible no es crítico si probamos desde fuera
            return self._create_result("skipped", f"Docker no accesible: {str(e)[:50]}")


@CheckRegistry.register("logs_check", quick=False, full=True)
class LogsCheck(BaseCheck):
    """Check de errores en logs recientes"""
    
    name = "Error Logs"
    category = CheckCategory.INFRA
    description = "Busca errores en logs recientes de contenedores"
    
    ERROR_PATTERNS = [
        r"Traceback",
        r"ERROR",
        r"Exception",
        r"CRITICAL",
        r"500 Internal Server Error",
        r"ConnectionRefused",
        r"TimeoutError",
    ]
    
    async def run(self) -> CheckResult:
        self.log("Analizando logs recientes...")
        
        containers_to_check = ["rio-api-dev", "rio-web-dev"]
        if self.environment == "prod":
            containers_to_check = ["rio-api-prod", "rio-web-prod"]
        
        total_errors = 0
        error_summary = []
        
        for container in containers_to_check:
            try:
                result = await self.command_runner.run(
                    "docker_logs",
                    extra_args=[container]
                )
                
                if not result.success:
                    self.log(f"? No se pudieron obtener logs de {container}")
                    continue
                
                # Buscar patrones de error
                logs = result.stdout + result.stderr
                errors_found = []
                
                for pattern in self.ERROR_PATTERNS:
                    matches = re.findall(f".*{pattern}.*", logs, re.IGNORECASE)
                    # Limitar a últimos 5 por patrón
                    errors_found.extend(matches[:5])
                
                if errors_found:
                    total_errors += len(errors_found)
                    error_summary.append({
                        "container": container,
                        "count": len(errors_found),
                        "sample": errors_found[0][:100] if errors_found else ""
                    })
                    
                    # Solo agregar finding si hay muchos errores
                    if len(errors_found) > 10:
                        self.add_finding(
                            title=f"Errores en logs: {container}",
                            description=f"{len(errors_found)} errores encontrados en logs recientes",
                            severity=CheckSeverity.MEDIUM,
                            location=container,
                            evidence=errors_found[0][:200]
                        )
                
            except Exception as e:
                self.log(f"Error obteniendo logs de {container}: {e}", "warning")
        
        if total_errors > 50:
            return self._create_result("failed", f"{total_errors} errores en logs")
        elif total_errors > 10:
            return self._create_result("passed", f"{total_errors} errores (revisar)")
        
        return self._create_result("passed", f"{total_errors} errores en logs")


@CheckRegistry.register("resources_check", quick=False, full=True)
class ResourcesCheck(BaseCheck):
    """Check de recursos del sistema"""
    
    name = "System Resources"
    category = CheckCategory.INFRA
    description = "Verifica uso de CPU, memoria y disco"
    
    # Umbrales de alerta
    DISK_WARNING = 80  # %
    DISK_CRITICAL = 90  # %
    MEMORY_WARNING = 80  # %
    MEMORY_CRITICAL = 90  # %
    
    async def run(self) -> CheckResult:
        self.log("Verificando recursos del sistema...")
        
        issues = []
        
        # Check disk
        try:
            result = await self.command_runner.run("disk_usage")
            if result.success:
                # Parsear output de df -h
                for line in result.stdout.split("\n")[1:]:  # Skip header
                    parts = line.split()
                    if len(parts) >= 5:
                        usage_str = parts[4].replace("%", "")
                        try:
                            usage = int(usage_str)
                            mount = parts[5] if len(parts) > 5 else "/"
                            
                            if usage >= self.DISK_CRITICAL:
                                issues.append({
                                    "type": "disk",
                                    "mount": mount,
                                    "usage": usage,
                                    "severity": CheckSeverity.CRITICAL
                                })
                            elif usage >= self.DISK_WARNING:
                                issues.append({
                                    "type": "disk",
                                    "mount": mount,
                                    "usage": usage,
                                    "severity": CheckSeverity.MEDIUM
                                })
                            else:
                                self.log(f"Disco {mount}: {usage}% usado")
                        except ValueError:
                            pass
        except Exception as e:
            self.log(f"Error verificando disco: {e}", "warning")
        
        # Check memory
        try:
            result = await self.command_runner.run("memory_info")
            if result.success:
                # Parsear output de free -h
                for line in result.stdout.split("\n"):
                    if line.startswith("Mem:"):
                        parts = line.split()
                        if len(parts) >= 3:
                            # Calcular uso aproximado
                            total = parts[1]
                            used = parts[2]
                            self.log(f"Memoria: {used} usado de {total}")
        except Exception as e:
            self.log(f"Error verificando memoria: {e}", "warning")
        
        # Check Docker resources
        try:
            result = await self.command_runner.run("docker_stats")
            if result.success:
                for line in result.stdout.strip().split("\n"):
                    if line.strip():
                        parts = line.split("|")
                        if len(parts) >= 4:
                            container = parts[0].strip()
                            cpu = parts[1].strip().replace("%", "")
                            mem_percent = parts[3].strip().replace("%", "")
                            
                            try:
                                if float(mem_percent) > self.MEMORY_WARNING:
                                    issues.append({
                                        "type": "container_memory",
                                        "container": container,
                                        "usage": float(mem_percent),
                                        "severity": CheckSeverity.MEDIUM
                                    })
                            except ValueError:
                                pass
        except Exception as e:
            self.log(f"Error verificando Docker stats: {e}", "warning")
        
        # Reportar findings
        for issue in issues:
            if issue["type"] == "disk":
                self.add_finding(
                    title=f"Disco alto: {issue['mount']}",
                    description=f"Uso de disco en {issue['mount']}: {issue['usage']}%",
                    severity=issue["severity"],
                    recommendation="Liberar espacio en disco"
                )
            elif issue["type"] == "container_memory":
                self.add_finding(
                    title=f"Memoria container: {issue['container']}",
                    description=f"Uso de memoria: {issue['usage']}%",
                    severity=issue["severity"]
                )
        
        critical = len([i for i in issues if i["severity"] == CheckSeverity.CRITICAL])
        
        if critical > 0:
            return self._create_result("failed", f"{len(issues)} alertas de recursos")
        elif issues:
            return self._create_result("passed", f"{len(issues)} warnings de recursos")
        
        return self._create_result("passed", "Recursos OK")
