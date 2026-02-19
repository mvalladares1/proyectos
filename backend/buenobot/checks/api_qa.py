"""
BUENOBOT - API QA Checks

Checks de calidad de API:
- Health check endpoints
- Smoke tests de endpoints críticos
- Validación de autenticación
- CORS y headers
"""
import asyncio
import httpx
from typing import List, Dict, Any, Optional

from .base import BaseCheck, CheckRegistry
from ..models import CheckResult, CheckCategory, CheckSeverity


@CheckRegistry.register("health_check", quick=True, full=True)
class HealthCheck(BaseCheck):
    """Check de endpoints de salud"""
    
    name = "Health Endpoints"
    category = CheckCategory.API_QA
    description = "Verifica que los endpoints de salud respondan correctamente"
    
    HEALTH_ENDPOINTS = [
        "/health",
        "/",
    ]
    
    async def run(self) -> CheckResult:
        self.log(f"Verificando endpoints de salud en {self.api_base_url}...")
        
        passed = []
        failed = []
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for endpoint in self.HEALTH_ENDPOINTS:
                url = f"{self.api_base_url}{endpoint}"
                try:
                    response = await client.get(url)
                    
                    if response.status_code == 200:
                        passed.append(endpoint)
                        self.log(f"✓ {endpoint} - OK (200)")
                    else:
                        failed.append((endpoint, response.status_code))
                        self.add_finding(
                            title=f"Health endpoint fallando",
                            description=f"{endpoint} retornó {response.status_code}",
                            severity=CheckSeverity.CRITICAL,
                            location=url
                        )
                except httpx.TimeoutException:
                    failed.append((endpoint, "timeout"))
                    self.add_finding(
                        title=f"Health endpoint timeout",
                        description=f"{endpoint} no respondió en 10s",
                        severity=CheckSeverity.CRITICAL,
                        location=url
                    )
                except httpx.ConnectError as e:
                    failed.append((endpoint, "connection_error"))
                    self.add_finding(
                        title=f"API no accesible",
                        description=f"No se pudo conectar a {url}: {str(e)}",
                        severity=CheckSeverity.CRITICAL,
                        location=url,
                        recommendation="Verificar que el contenedor API esté corriendo"
                    )
        
        if failed:
            return self._create_result(
                "failed",
                f"{len(passed)}/{len(self.HEALTH_ENDPOINTS)} endpoints OK"
            )
        
        return self._create_result(
            "passed",
            f"Todos los health endpoints OK"
        )


@CheckRegistry.register("endpoint_smoke", quick=False, full=True)
class EndpointSmokeCheck(BaseCheck):
    """Smoke test de endpoints críticos por router"""
    
    name = "Endpoint Smoke Tests"
    category = CheckCategory.API_QA
    description = "Verifica que endpoints críticos respondan (sin auth)"
    
    # Endpoints públicos o con respuesta conocida sin auth
    SMOKE_ENDPOINTS = [
        # Formato: (método, path, expected_status_without_auth)
        ("GET", "/docs", 200),
        ("GET", "/redoc", 200),
        ("GET", "/api/v1/cache/stats", 200),
        # Endpoints protegidos deben retornar 401/403
        ("GET", "/api/v1/produccion/ordenes", [401, 403, 422]),
        ("GET", "/api/v1/stock/movimientos", [401, 403, 422]),
        ("GET", "/api/v1/permissions", [401, 403, 422]),
    ]
    
    async def run(self) -> CheckResult:
        self.log(f"Ejecutando smoke tests en {self.api_base_url}...")
        
        total = len(self.SMOKE_ENDPOINTS)
        passed = 0
        failed_endpoints = []
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            for method, path, expected in self.SMOKE_ENDPOINTS:
                url = f"{self.api_base_url}{path}"
                
                try:
                    if method == "GET":
                        response = await client.get(url)
                    elif method == "POST":
                        response = await client.post(url, json={})
                    else:
                        continue
                    
                    # Verificar status esperado
                    if isinstance(expected, list):
                        is_ok = response.status_code in expected
                    else:
                        is_ok = response.status_code == expected
                    
                    if is_ok:
                        passed += 1
                        self.log(f"✓ {method} {path} - {response.status_code}")
                    else:
                        failed_endpoints.append({
                            "method": method,
                            "path": path,
                            "expected": expected,
                            "got": response.status_code
                        })
                        self.log(f"✗ {method} {path} - Expected {expected}, got {response.status_code}", "warning")
                        
                except Exception as e:
                    failed_endpoints.append({
                        "method": method,
                        "path": path,
                        "expected": expected,
                        "got": str(e)
                    })
                    self.log(f"✗ {method} {path} - Error: {e}", "error")
        
        for fail in failed_endpoints:
            self.add_finding(
                title=f"Endpoint {fail['method']} {fail['path']} inesperado",
                description=f"Esperado: {fail['expected']}, Obtenido: {fail['got']}",
                severity=CheckSeverity.MEDIUM,
                location=fail['path']
            )
        
        status = "passed" if passed >= total * 0.8 else "failed"  # 80% threshold
        return self._create_result(status, f"{passed}/{total} endpoints OK")


@CheckRegistry.register("auth_check", quick=True, full=True)
class AuthCheck(BaseCheck):
    """Verifica que endpoints protegidos requieran autenticación"""
    
    name = "Authentication Check"
    category = CheckCategory.API_QA
    description = "Verifica que endpoints protegidos no sean accesibles sin auth"
    
    # Endpoints que DEBEN requerir autenticación
    PROTECTED_ENDPOINTS = [
        "/api/v1/permissions",
        "/api/v1/produccion/ordenes",
        "/api/v1/stock/movimientos",
        "/api/v1/bandejas/escaner",
        "/api/v1/compras/ordenes",
        "/api/v1/automatizaciones/crear-orden",
        "/api/v1/comercial/clientes",
        "/api/v1/reconciliacion/odf",
    ]
    
    # Status codes que indican auth requerida
    AUTH_REQUIRED_STATUS = [401, 403, 422]
    
    async def run(self) -> CheckResult:
        self.log("Verificando protección de endpoints...")
        
        vulnerable = []
        protected = []
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for endpoint in self.PROTECTED_ENDPOINTS:
                url = f"{self.api_base_url}{endpoint}"
                
                try:
                    # Intentar acceder SIN autenticación
                    response = await client.get(url)
                    
                    if response.status_code in self.AUTH_REQUIRED_STATUS:
                        protected.append(endpoint)
                        self.log(f"✓ {endpoint} - Protegido ({response.status_code})")
                    elif response.status_code == 200:
                        # CRÍTICO: endpoint accesible sin auth
                        vulnerable.append(endpoint)
                        self.add_finding(
                            title="Endpoint accesible sin autenticación",
                            description=f"{endpoint} retornó 200 sin credenciales",
                            severity=CheckSeverity.CRITICAL,
                            location=endpoint,
                            recommendation="Agregar validación de autenticación"
                        )
                        self.log(f"✗ {endpoint} - VULNERABLE (200 sin auth)", "error")
                    else:
                        # Otros status (404, 500) - check pero no es crítico
                        self.log(f"? {endpoint} - Status {response.status_code}")
                        
                except httpx.ConnectError:
                    self.log(f"? {endpoint} - No se pudo conectar", "warning")
                except Exception as e:
                    self.log(f"? {endpoint} - Error: {e}", "warning")
        
        if vulnerable:
            return self._create_result(
                "failed",
                f"¡{len(vulnerable)} endpoints vulnerables!"
            )
        
        return self._create_result(
            "passed",
            f"{len(protected)}/{len(self.PROTECTED_ENDPOINTS)} endpoints protegidos"
        )


@CheckRegistry.register("cors_headers", quick=False, full=True)
class CORSHeadersCheck(BaseCheck):
    """Verifica configuración de CORS y headers de seguridad"""
    
    name = "CORS & Headers"
    category = CheckCategory.API_QA
    description = "Verifica headers de seguridad y configuración CORS"
    
    async def run(self) -> CheckResult:
        self.log("Verificando CORS y headers...")
        
        issues = []
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # OPTIONS request para CORS
                response = await client.options(
                    f"{self.api_base_url}/health",
                    headers={"Origin": "https://malicious-site.com"}
                )
                
                # Verificar Access-Control-Allow-Origin
                acao = response.headers.get("access-control-allow-origin", "")
                
                if acao == "*":
                    # En desarrollo puede ser OK, en prod no
                    if self.environment == "prod":
                        issues.append({
                            "header": "Access-Control-Allow-Origin",
                            "value": acao,
                            "issue": "CORS permite cualquier origen en producción",
                            "severity": CheckSeverity.HIGH
                        })
                    else:
                        issues.append({
                            "header": "Access-Control-Allow-Origin",
                            "value": acao,
                            "issue": "CORS permite cualquier origen (OK en dev)",
                            "severity": CheckSeverity.LOW
                        })
                
                # GET para verificar otros headers
                response = await client.get(f"{self.api_base_url}/health")
                
                # Headers de seguridad recomendados
                security_headers = {
                    "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": ["DENY", "SAMEORIGIN"],
                }
                
                for header, expected in security_headers.items():
                    value = response.headers.get(header)
                    if not value:
                        issues.append({
                            "header": header,
                            "value": "missing",
                            "issue": f"Header de seguridad {header} no presente",
                            "severity": CheckSeverity.LOW
                        })
                
            except Exception as e:
                self.log(f"Error verificando headers: {e}", "error")
                return self._create_result("error", str(e))
        
        for issue in issues:
            self.add_finding(
                title=f"Header: {issue['header']}",
                description=issue['issue'],
                severity=issue['severity'],
                recommendation=f"Configurar header {issue['header']} correctamente"
            )
        
        high_issues = len([i for i in issues if i['severity'] in [CheckSeverity.HIGH, CheckSeverity.CRITICAL]])
        
        if high_issues > 0:
            return self._create_result("failed", f"{len(issues)} problemas de headers")
        
        return self._create_result("passed", f"{len(issues)} advertencias menores")
