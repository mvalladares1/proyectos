"""
BUENOBOT - Odoo Integrity Checks

Checks de integridad de integración con Odoo:
- Conectividad
- Smoke queries
- Timeouts/retries configurados
"""
import os
import asyncio
from typing import Optional

from .base import BaseCheck, CheckRegistry
from ..models import CheckResult, CheckCategory, CheckSeverity


@CheckRegistry.register("odoo_connectivity", quick=True, full=True)
class OdooConnectivityCheck(BaseCheck):
    """Check de conectividad con Odoo"""
    
    name = "Odoo Connectivity"
    category = CheckCategory.ODOO_INTEGRITY
    description = "Verifica conexión y autenticación con Odoo"
    
    async def run(self) -> CheckResult:
        self.log("Verificando conectividad con Odoo...")
        
        # Obtener configuración de Odoo
        odoo_url = os.environ.get("ODOO_URL", "")
        odoo_db = os.environ.get("ODOO_DB", "")
        
        if not odoo_url or not odoo_db:
            self.add_finding(
                title="Configuración Odoo incompleta",
                description="ODOO_URL o ODOO_DB no están configurados",
                severity=CheckSeverity.MEDIUM,
                recommendation="Verificar variables de entorno ODOO_URL y ODOO_DB"
            )
            return self._create_result("skipped", "Configuración Odoo no disponible")
        
        self.log(f"Odoo URL: {odoo_url}")
        self.log(f"Odoo DB: {odoo_db}")
        
        # Verificar que la URL sea accesible
        import httpx
        
        try:
            async with httpx.AsyncClient(timeout=15.0, verify=False) as client:
                # Test 1: Version endpoint (público)
                version_url = f"{odoo_url}/web/webclient/version_info"
                response = await client.get(version_url)
                
                if response.status_code == 200:
                    self.log("✓ Odoo accesible (version endpoint)")
                else:
                    self.add_finding(
                        title="Odoo no accesible",
                        description=f"Version endpoint retornó {response.status_code}",
                        severity=CheckSeverity.HIGH,
                        location=version_url
                    )
                    return self._create_result("failed", "Odoo no accesible")
                
                # Test 2: Database list (si está habilitado)
                db_url = f"{odoo_url}/web/database/list"
                try:
                    response = await client.post(db_url, json={"params": {}})
                    if response.status_code == 200:
                        data = response.json()
                        dbs = data.get("result", [])
                        if odoo_db in dbs:
                            self.log(f"✓ Base de datos '{odoo_db}' encontrada")
                        else:
                            self.add_finding(
                                title="Base de datos no encontrada",
                                description=f"La DB '{odoo_db}' no está en la lista",
                                severity=CheckSeverity.MEDIUM,
                                recommendation="Verificar nombre de base de datos"
                            )
                except Exception:
                    # Database list puede estar deshabilitado
                    self.log("? Database list no disponible (normal en producción)")
            
            return self._create_result("passed", "Conectividad Odoo OK")
            
        except httpx.TimeoutException:
            self.add_finding(
                title="Timeout conectando a Odoo",
                description=f"No se pudo conectar a {odoo_url} en 15s",
                severity=CheckSeverity.HIGH,
                recommendation="Verificar conectividad de red"
            )
            return self._create_result("failed", "Timeout de conexión")
        except Exception as e:
            self.add_finding(
                title="Error de conexión Odoo",
                description=str(e),
                severity=CheckSeverity.HIGH
            )
            return self._create_result("failed", f"Error: {str(e)[:50]}")


@CheckRegistry.register("odoo_config", quick=False, full=True)
class OdooConfigCheck(BaseCheck):
    """Check de configuración de cliente Odoo"""
    
    name = "Odoo Client Config"
    category = CheckCategory.ODOO_INTEGRITY
    description = "Verifica configuración de timeouts y retries del cliente Odoo"
    
    async def run(self) -> CheckResult:
        self.log("Verificando configuración cliente Odoo...")
        
        # Buscar archivo odoo_client.py
        client_path = os.path.join(self.working_dir, "shared", "odoo_client.py")
        
        if not os.path.exists(client_path):
            self.add_finding(
                title="odoo_client.py no encontrado",
                description="El archivo shared/odoo_client.py no existe",
                severity=CheckSeverity.MEDIUM
            )
            return self._create_result("skipped", "Cliente Odoo no encontrado")
        
        try:
            with open(client_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            issues = []
            
            # Verificar timeout configurado
            if "timeout" not in content.lower():
                issues.append({
                    "issue": "Sin timeout configurado",
                    "severity": CheckSeverity.MEDIUM,
                    "recommendation": "Agregar timeout a las llamadas XML-RPC"
                })
            
            # Verificar retries
            if "retry" not in content.lower() and "retries" not in content.lower():
                issues.append({
                    "issue": "Sin manejo de reintentos",
                    "severity": CheckSeverity.LOW,
                    "recommendation": "Implementar retry logic para llamadas a Odoo"
                })
            
            # Verificar manejo de errores
            if "try:" not in content or "except" not in content:
                issues.append({
                    "issue": "Sin manejo de excepciones visible",
                    "severity": CheckSeverity.LOW
                })
            
            # Verificar que no hay credenciales hardcodeadas
            if "password" in content and "=" in content:
                import re
                if re.search(r'password\s*=\s*["\'][^"\']+["\']', content):
                    issues.append({
                        "issue": "Posible password hardcodeado",
                        "severity": CheckSeverity.HIGH,
                        "recommendation": "Mover a variables de entorno"
                    })
            
            for issue in issues:
                self.add_finding(
                    title=f"Config Odoo: {issue['issue']}",
                    description=issue['issue'],
                    severity=issue.get('severity', CheckSeverity.LOW),
                    location="shared/odoo_client.py",
                    recommendation=issue.get('recommendation', '')
                )
            
            high_issues = len([i for i in issues if i.get('severity') == CheckSeverity.HIGH])
            
            if high_issues > 0:
                return self._create_result("failed", f"{len(issues)} problemas de configuración")
            
            return self._create_result("passed", f"{len(issues)} advertencias menores")
            
        except Exception as e:
            return self._create_result("error", str(e))
