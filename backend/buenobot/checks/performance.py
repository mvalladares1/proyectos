"""
BUENOBOT - Performance Checks

Checks de rendimiento:
- Tiempo de respuesta de endpoints
- Detección de endpoints lentos
- P95 simple
"""
import asyncio
import time
import statistics
from typing import List, Dict, Any

import httpx

from .base import BaseCheck, CheckRegistry
from ..models import CheckResult, CheckCategory, CheckSeverity


@CheckRegistry.register("endpoint_performance", quick=False, full=True)
class EndpointPerformanceCheck(BaseCheck):
    """Check de rendimiento de endpoints"""
    
    name = "Endpoint Performance"
    category = CheckCategory.PERFORMANCE
    description = "Mide tiempos de respuesta de endpoints críticos"
    
    # Endpoints a medir con umbral máximo aceptable (ms)
    ENDPOINTS_TO_TEST = [
        ("/health", 500),
        ("/", 500),
        ("/docs", 2000),
        ("/api/v1/cache/stats", 1000),
    ]
    
    REQUESTS_PER_ENDPOINT = 5  # Número de requests para calcular métricas
    SLOW_THRESHOLD_MS = 2000  # Umbral general para "lento"
    
    async def run(self) -> CheckResult:
        self.log("Ejecutando tests de rendimiento...")
        
        results = []
        slow_endpoints = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for endpoint, max_time in self.ENDPOINTS_TO_TEST:
                url = f"{self.api_base_url}{endpoint}"
                times = []
                errors = 0
                
                for i in range(self.REQUESTS_PER_ENDPOINT):
                    try:
                        start = time.time()
                        response = await client.get(url)
                        elapsed = (time.time() - start) * 1000  # ms
                        
                        if response.status_code == 200:
                            times.append(elapsed)
                        else:
                            errors += 1
                            
                    except Exception as e:
                        errors += 1
                        self.log(f"Error en {endpoint}: {e}", "warning")
                    
                    # Pequeña pausa entre requests
                    await asyncio.sleep(0.1)
                
                if times:
                    avg = statistics.mean(times)
                    p95 = sorted(times)[int(len(times) * 0.95)] if len(times) > 1 else times[0]
                    min_time = min(times)
                    max_time_measured = max(times)
                    
                    result_entry = {
                        "endpoint": endpoint,
                        "avg_ms": round(avg, 2),
                        "p95_ms": round(p95, 2),
                        "min_ms": round(min_time, 2),
                        "max_ms": round(max_time_measured, 2),
                        "requests": len(times),
                        "errors": errors,
                        "threshold": max_time
                    }
                    results.append(result_entry)
                    
                    self.log(f"{endpoint}: avg={avg:.0f}ms, p95={p95:.0f}ms")
                    
                    # Evaluar si es lento
                    if p95 > max_time:
                        slow_endpoints.append(result_entry)
                        self.add_finding(
                            title=f"Endpoint lento: {endpoint}",
                            description=f"P95: {p95:.0f}ms (umbral: {max_time}ms)",
                            severity=CheckSeverity.MEDIUM if p95 < max_time * 2 else CheckSeverity.HIGH,
                            location=endpoint,
                            evidence=f"avg={avg:.0f}ms, min={min_time:.0f}ms, max={max_time_measured:.0f}ms",
                            recommendation="Optimizar endpoint o aumentar recursos"
                        )
                else:
                    self.log(f"✗ {endpoint}: todos los requests fallaron", "error")
                    self.add_finding(
                        title=f"Endpoint no responde: {endpoint}",
                        description=f"Todos los {self.REQUESTS_PER_ENDPOINT} requests fallaron",
                        severity=CheckSeverity.HIGH,
                        location=endpoint
                    )
        
        # Calcular métricas globales
        if results:
            all_p95 = [r["p95_ms"] for r in results]
            global_avg_p95 = statistics.mean(all_p95)
            
            summary = f"P95 promedio: {global_avg_p95:.0f}ms, {len(slow_endpoints)} endpoints lentos"
            
            if len(slow_endpoints) > len(results) / 2:
                return self._create_result("failed", summary)
            elif slow_endpoints:
                return self._create_result("passed", summary)
            
            return self._create_result("passed", f"P95 promedio: {global_avg_p95:.0f}ms - OK")
        
        return self._create_result("failed", "No se pudieron medir endpoints")


@CheckRegistry.register("api_latency", quick=True, full=True)
class APILatencyCheck(BaseCheck):
    """Check rápido de latencia de API"""
    
    name = "API Latency"
    category = CheckCategory.PERFORMANCE
    description = "Verifica latencia básica del API"
    
    MAX_HEALTH_LATENCY_MS = 500
    
    async def run(self) -> CheckResult:
        self.log("Midiendo latencia de health endpoint...")
        
        url = f"{self.api_base_url}/health"
        times = []
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for i in range(3):
                try:
                    start = time.time()
                    response = await client.get(url)
                    elapsed = (time.time() - start) * 1000
                    
                    if response.status_code == 200:
                        times.append(elapsed)
                except Exception as e:
                    self.log(f"Error: {e}", "warning")
                
                await asyncio.sleep(0.1)
        
        if not times:
            self.add_finding(
                title="API no responde",
                description=f"No se pudo conectar a {url}",
                severity=CheckSeverity.CRITICAL
            )
            return self._create_result("failed", "API no responde")
        
        avg = statistics.mean(times)
        
        if avg > self.MAX_HEALTH_LATENCY_MS:
            self.add_finding(
                title="Latencia alta",
                description=f"Health endpoint: {avg:.0f}ms (umbral: {self.MAX_HEALTH_LATENCY_MS}ms)",
                severity=CheckSeverity.MEDIUM
            )
            return self._create_result("passed", f"Latencia: {avg:.0f}ms (alto)")
        
        return self._create_result("passed", f"Latencia: {avg:.0f}ms")
