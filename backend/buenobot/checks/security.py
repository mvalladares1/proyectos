"""
BUENOBOT - Security Checks

Checks de seguridad:
- Pip Audit (vulnerabilidades en dependencias)
- Bandit (análisis estático de seguridad)
- Secrets (detección de credenciales)
- Docker misconfig
"""
import json
import re
import os
from typing import List, Dict, Any

from .base import BaseCheck, CheckRegistry
from ..models import CheckResult, CheckCategory, CheckSeverity


@CheckRegistry.register("pip_audit", quick=True, full=True)
class PipAuditCheck(BaseCheck):
    """Check de vulnerabilidades en dependencias"""
    
    name = "Pip Audit"
    category = CheckCategory.SECURITY
    description = "Audita dependencias Python por vulnerabilidades conocidas"
    
    async def run(self) -> CheckResult:
        self.log("Ejecutando pip-audit...")
        
        try:
            result = await self.command_runner.run("pip_audit")
            
            if result.success and not result.stdout.strip():
                self.log("Sin vulnerabilidades encontradas")
                return self._create_result("passed", "Sin vulnerabilidades")
            
            # Parsear output JSON
            vulns = self._parse_audit_output(result.stdout)
            
            critical_count = 0
            high_count = 0
            medium_count = 0
            
            for vuln in vulns:
                severity = self._classify_severity(vuln)
                
                if severity == CheckSeverity.CRITICAL:
                    critical_count += 1
                elif severity == CheckSeverity.HIGH:
                    high_count += 1
                else:
                    medium_count += 1
                
                self.add_finding(
                    title=f"Vulnerabilidad: {vuln.get('id', 'Unknown')}",
                    description=f"{vuln.get('name', '')} {vuln.get('version', '')} - {vuln.get('description', '')}",
                    severity=severity,
                    location=f"{vuln.get('name', '')}=={vuln.get('version', '')}",
                    evidence=vuln.get('id', ''),
                    recommendation=f"Actualizar a {vuln.get('fix_versions', ['versión segura'])[0] if vuln.get('fix_versions') else 'versión segura'}"
                )
            
            # Gate: FAIL si hay critical o high
            if critical_count > 0 or high_count > 0:
                status = "failed"
            elif medium_count > 0:
                status = "passed"  # Medium solo warning
            else:
                status = "passed"
            
            summary = f"Critical: {critical_count}, High: {high_count}, Medium: {medium_count}"
            return self._create_result(status, summary)
            
        except Exception as e:
            self.log(f"Error: {e}", "error")
            # Si pip-audit no está instalado, marcar como skipped
            if "No module named" in str(e) or "not found" in str(e).lower():
                return self._create_result("skipped", "pip-audit no instalado")
            return self._create_result("error", str(e))
    
    def _parse_audit_output(self, output: str) -> List[Dict[str, Any]]:
        """Parsea output JSON de pip-audit"""
        try:
            data = json.loads(output)
            if isinstance(data, list):
                return data
            return data.get("vulnerabilities", [])
        except json.JSONDecodeError:
            return []
    
    def _classify_severity(self, vuln: Dict[str, Any]) -> CheckSeverity:
        """Clasifica severidad basada en aliases (CVE)"""
        aliases = vuln.get("aliases", [])
        desc = vuln.get("description", "").lower()
        
        # Heurística simple
        if any(kw in desc for kw in ["remote code execution", "rce", "critical"]):
            return CheckSeverity.CRITICAL
        elif any(kw in desc for kw in ["injection", "authentication bypass", "high"]):
            return CheckSeverity.HIGH
        return CheckSeverity.MEDIUM


@CheckRegistry.register("bandit_scan", quick=False, full=True)
class BanditCheck(BaseCheck):
    """Check de seguridad estática con Bandit"""
    
    name = "Bandit Security Scan"
    category = CheckCategory.SECURITY
    description = "Análisis estático de seguridad en código Python"
    
    async def run(self) -> CheckResult:
        self.log("Ejecutando Bandit...")
        
        try:
            result = await self.command_runner.run(
                "bandit_scan",
                extra_args=["backend/"]
            )
            
            # Bandit retorna código no-cero si encuentra issues
            issues = self._parse_bandit_output(result.stdout)
            
            if not issues:
                return self._create_result("passed", "Sin problemas de seguridad")
            
            high_count = 0
            medium_count = 0
            
            for issue in issues:
                severity = CheckSeverity.HIGH if issue.get("severity") == "HIGH" else CheckSeverity.MEDIUM
                
                if severity == CheckSeverity.HIGH:
                    high_count += 1
                else:
                    medium_count += 1
                
                self.add_finding(
                    title=f"Security: {issue.get('test_id', '')} - {issue.get('test_name', '')}",
                    description=issue.get("issue_text", ""),
                    severity=severity,
                    location=f"{issue.get('filename', '')}:{issue.get('line_number', '')}",
                    evidence=issue.get("code", "")[:200],
                    recommendation=issue.get("more_info", "")
                )
            
            status = "failed" if high_count > 0 else "passed"
            summary = f"High: {high_count}, Medium: {medium_count}"
            return self._create_result(status, summary)
            
        except Exception as e:
            self.log(f"Error: {e}", "error")
            if "No module named" in str(e):
                return self._create_result("skipped", "Bandit no instalado")
            return self._create_result("error", str(e))
    
    def _parse_bandit_output(self, output: str) -> List[Dict[str, Any]]:
        """Parsea output JSON de bandit"""
        try:
            data = json.loads(output)
            return data.get("results", [])
        except json.JSONDecodeError:
            return []


@CheckRegistry.register("secrets_scan", quick=True, full=True)
class SecretsCheck(BaseCheck):
    """Check de secretos y credenciales expuestas"""
    
    name = "Secrets Scanner"
    category = CheckCategory.SECURITY
    description = "Detecta credenciales y secretos hardcodeados"
    
    # Patrones de secretos comunes
    SECRET_PATTERNS = [
        (r'password\s*=\s*["\'][^"\']{6,}["\']', "Hardcoded password"),
        (r'api[_-]?key\s*=\s*["\'][^"\']{10,}["\']', "Hardcoded API key"),
        (r'secret[_-]?key\s*=\s*["\'][^"\']{10,}["\']', "Hardcoded secret key"),
        (r'token\s*=\s*["\'][^"\']{10,}["\']', "Hardcoded token"),
        (r'AWS[A-Z0-9]{16,}', "Possible AWS key"),
        (r'sk-[a-zA-Z0-9]{32,}', "Possible OpenAI key"),
        (r'ghp_[a-zA-Z0-9]{36}', "GitHub personal access token"),
        (r'xox[baprs]-[0-9]{10,}-[a-zA-Z0-9]{10,}', "Slack token"),
        (r'-----BEGIN (RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----', "Private key"),
    ]
    
    # Archivos a ignorar
    IGNORE_FILES = [
        ".env.example",
        "test_",
        "_test.py",
        "mock",
        "__pycache__",
        ".git",
        "node_modules",
    ]
    
    async def run(self) -> CheckResult:
        self.log("Buscando secretos en código...")
        
        secrets_found = []
        files_scanned = 0
        
        try:
            for root, dirs, files in os.walk(self.working_dir):
                # Filtrar directorios
                dirs[:] = [d for d in dirs if not any(ign in d for ign in self.IGNORE_FILES)]
                
                for file in files:
                    if not file.endswith(('.py', '.json', '.yml', '.yaml', '.env', '.conf', '.ini')):
                        continue
                    
                    if any(ign in file for ign in self.IGNORE_FILES):
                        continue
                    
                    filepath = os.path.join(root, file)
                    rel_path = os.path.relpath(filepath, self.working_dir)
                    
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        
                        files_scanned += 1
                        
                        for pattern, desc in self.SECRET_PATTERNS:
                            matches = re.finditer(pattern, content, re.IGNORECASE)
                            for match in matches:
                                # Evitar falsos positivos obvios
                                matched_text = match.group()
                                if self._is_false_positive(matched_text, content):
                                    continue
                                
                                line_num = content[:match.start()].count('\n') + 1
                                secrets_found.append({
                                    "file": rel_path,
                                    "line": line_num,
                                    "type": desc,
                                    "snippet": self._sanitize_snippet(matched_text)
                                })
                    except Exception as e:
                        self.log(f"Error leyendo {rel_path}: {e}", "warning")
            
            # Reportar hallazgos
            for secret in secrets_found[:10]:  # Limitar
                self.add_finding(
                    title=f"Secret: {secret['type']}",
                    description=f"Posible {secret['type']} detectado",
                    severity=CheckSeverity.CRITICAL,
                    location=f"{secret['file']}:{secret['line']}",
                    evidence=secret['snippet'],
                    recommendation="Mover a variables de entorno y rotar la credencial"
                )
            
            if secrets_found:
                return self._create_result(
                    "failed",
                    f"{len(secrets_found)} secretos encontrados en {files_scanned} archivos"
                )
            
            return self._create_result(
                "passed",
                f"Sin secretos en {files_scanned} archivos"
            )
            
        except Exception as e:
            self.log(f"Error: {e}", "error")
            return self._create_result("error", str(e))
    
    def _is_false_positive(self, match: str, context: str) -> bool:
        """Detecta falsos positivos comunes"""
        # Env var references
        if "os.environ" in context or "os.getenv" in context:
            return True
        # Placeholder values
        if any(ph in match.lower() for ph in ["example", "placeholder", "change_me", "xxx", "your_"]):
            return True
        # In comments
        if match.startswith("#"):
            return True
        return False
    
    def _sanitize_snippet(self, text: str) -> str:
        """Sanitiza el snippet para no mostrar el secreto completo"""
        if len(text) > 20:
            return text[:10] + "..." + text[-5:]
        return text[:5] + "***"


@CheckRegistry.register("docker_security", quick=False, full=True)
class DockerSecurityCheck(BaseCheck):
    """Check de configuración segura de Docker"""
    
    name = "Docker Security"
    category = CheckCategory.SECURITY
    description = "Verifica configuración segura de Docker/Compose"
    
    async def run(self) -> CheckResult:
        self.log("Analizando configuración Docker...")
        
        issues = []
        
        try:
            # Revisar docker-compose files
            compose_files = [
                "docker-compose.yml",
                "docker-compose.dev.yml",
                "docker-compose.prod.yml"
            ]
            
            for compose_file in compose_files:
                filepath = os.path.join(self.working_dir, compose_file)
                if os.path.exists(filepath):
                    with open(filepath, 'r') as f:
                        content = f.read()
                    
                    # Check: privileged containers
                    if "privileged: true" in content:
                        issues.append({
                            "file": compose_file,
                            "issue": "Container con privileged=true",
                            "severity": CheckSeverity.HIGH
                        })
                    
                    # Check: exposed ports sensibles
                    if ":22:" in content or ":3306:" in content or ":5432:" in content:
                        issues.append({
                            "file": compose_file,
                            "issue": "Puerto sensible expuesto (SSH/DB)",
                            "severity": CheckSeverity.MEDIUM
                        })
                    
                    # Check: root user
                    if "user: root" in content:
                        issues.append({
                            "file": compose_file,
                            "issue": "Container corriendo como root",
                            "severity": CheckSeverity.MEDIUM
                        })
                    
                    # Check: volume mounts sensibles
                    sensitive_paths = ["/etc", "/var/run/docker.sock", "/root"]
                    for path in sensitive_paths:
                        if f"- {path}" in content or f":{path}" in content:
                            issues.append({
                                "file": compose_file,
                                "issue": f"Volume mount sensible: {path}",
                                "severity": CheckSeverity.HIGH
                            })
            
            # Revisar Dockerfiles
            dockerfiles = ["Dockerfile", "Dockerfile.api", "Dockerfile.web"]
            for dockerfile in dockerfiles:
                filepath = os.path.join(self.working_dir, dockerfile)
                if os.path.exists(filepath):
                    with open(filepath, 'r') as f:
                        content = f.read()
                    
                    # Check: FROM latest
                    if "FROM" in content and ":latest" in content:
                        issues.append({
                            "file": dockerfile,
                            "issue": "Usando tag :latest (no reproducible)",
                            "severity": CheckSeverity.LOW
                        })
                    
                    # Check: ADD en lugar de COPY
                    if "ADD http" in content:
                        issues.append({
                            "file": dockerfile,
                            "issue": "Usando ADD con URL (preferir COPY + curl)",
                            "severity": CheckSeverity.LOW
                        })
            
            # Reportar
            for issue in issues:
                self.add_finding(
                    title=f"Docker: {issue['issue']}",
                    description=f"En {issue['file']}",
                    severity=issue['severity'],
                    location=issue['file'],
                    recommendation="Revisar configuración de seguridad Docker"
                )
            
            high_issues = len([i for i in issues if i['severity'] == CheckSeverity.HIGH])
            
            if high_issues > 0:
                return self._create_result("failed", f"{len(issues)} problemas de seguridad Docker")
            
            return self._create_result("passed", f"{len(issues)} advertencias Docker")
            
        except Exception as e:
            self.log(f"Error: {e}", "error")
            return self._create_result("error", str(e))
