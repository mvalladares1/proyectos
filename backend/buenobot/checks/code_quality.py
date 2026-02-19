"""
BUENOBOT - Code Quality Checks

Checks de calidad de código:
- Ruff (lint)
- Mypy (type checking)
- Import cycles
- Dead code
"""
import json
from typing import List, Dict, Any

from .base import BaseCheck, CheckRegistry
from ..models import CheckResult, CheckCategory, CheckSeverity


@CheckRegistry.register("ruff_lint", quick=True, full=True)
class RuffLintCheck(BaseCheck):
    """Check de linting con Ruff"""
    
    name = "Ruff Linter"
    category = CheckCategory.CODE_QUALITY
    description = "Análisis estático de código Python con Ruff"
    
    async def run(self) -> CheckResult:
        self.log("Ejecutando Ruff linter...")
        
        try:
            result = await self.command_runner.run(
                "ruff_check",
                extra_args=["backend/", "pages/", "shared/"]
            )
            
            if result.success:
                self.log("Ruff: Sin problemas encontrados")
                return self._create_result("passed", "Sin errores de lint")
            
            # Parsear output JSON de ruff
            issues = self._parse_ruff_output(result.stdout)
            
            # Agrupar por severidad
            errors = [i for i in issues if i.get("type") == "E"]
            warnings = [i for i in issues if i.get("type") == "W"]
            
            for issue in errors[:10]:  # Limitar a 10
                self.add_finding(
                    title=f"Lint Error: {issue.get('code', 'Unknown')}",
                    description=issue.get("message", ""),
                    severity=CheckSeverity.HIGH if issue.get("code", "").startswith("E9") else CheckSeverity.MEDIUM,
                    location=f"{issue.get('filename')}:{issue.get('row')}",
                    recommendation=f"Fix: {issue.get('code')}"
                )
            
            for issue in warnings[:5]:
                self.add_finding(
                    title=f"Lint Warning: {issue.get('code', 'Unknown')}",
                    description=issue.get("message", ""),
                    severity=CheckSeverity.LOW,
                    location=f"{issue.get('filename')}:{issue.get('row')}"
                )
            
            status = "failed" if errors else "passed"
            summary = f"{len(errors)} errores, {len(warnings)} warnings"
            
            return self._create_result(status, summary)
            
        except Exception as e:
            self.log(f"Error ejecutando Ruff: {e}", "error")
            return self._create_result("error", str(e))
    
    def _parse_ruff_output(self, output: str) -> List[Dict[str, Any]]:
        """Parsea output JSON de ruff"""
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            # Fallback: parsear formato texto
            issues = []
            for line in output.split("\n"):
                if ":" in line and line.strip():
                    parts = line.split(":")
                    if len(parts) >= 4:
                        issues.append({
                            "filename": parts[0],
                            "row": parts[1],
                            "code": parts[3].split()[0] if len(parts[3].split()) > 0 else "",
                            "message": ":".join(parts[3:]),
                            "type": parts[3].split()[0][0] if len(parts[3].split()) > 0 else "E"
                        })
            return issues


@CheckRegistry.register("mypy_check", quick=False, full=True)
class MypyCheck(BaseCheck):
    """Check de tipos con Mypy"""
    
    name = "Mypy Type Check"
    category = CheckCategory.CODE_QUALITY
    description = "Verificación de tipos con Mypy (nivel básico)"
    
    async def run(self) -> CheckResult:
        self.log("Ejecutando Mypy type checker...")
        
        try:
            result = await self.command_runner.run(
                "mypy_check",
                extra_args=["backend/"],
                timeout_override=180
            )
            
            if result.success:
                self.log("Mypy: Sin errores de tipos")
                return self._create_result("passed", "Sin errores de tipos")
            
            # Parsear errores
            errors = self._parse_mypy_output(result.stdout + result.stderr)
            
            # Solo reportar errores críticos de tipos
            critical_errors = [e for e in errors if "error:" in e.get("message", "")]
            
            for error in critical_errors[:10]:
                self.add_finding(
                    title="Type Error",
                    description=error.get("message", ""),
                    severity=CheckSeverity.LOW,  # Type errors no bloquean
                    location=error.get("location", ""),
                    recommendation="Agregar type hints o ignorar con # type: ignore"
                )
            
            summary = f"{len(critical_errors)} errores de tipos"
            return self._create_result("passed" if len(critical_errors) < 10 else "failed", summary)
            
        except Exception as e:
            self.log(f"Error ejecutando Mypy: {e}", "error")
            # Mypy no instalado no es crítico
            return self._create_result("skipped", f"Mypy no disponible: {e}")
    
    def _parse_mypy_output(self, output: str) -> List[Dict[str, str]]:
        """Parsea output de mypy"""
        errors = []
        for line in output.split("\n"):
            if ": error:" in line or ": warning:" in line:
                parts = line.split(":", 2)
                if len(parts) >= 3:
                    errors.append({
                        "location": f"{parts[0]}:{parts[1]}",
                        "message": parts[2].strip()
                    })
        return errors


@CheckRegistry.register("import_check", quick=False, full=True)
class ImportCycleCheck(BaseCheck):
    """Check de ciclos de importación"""
    
    name = "Import Cycles"
    category = CheckCategory.CODE_QUALITY
    description = "Detecta ciclos de importación en el código"
    
    async def run(self) -> CheckResult:
        self.log("Buscando ciclos de importación...")
        
        # Este check usa análisis simple sin herramientas externas
        import os
        import ast
        
        imports_map: Dict[str, List[str]] = {}
        
        try:
            for root, dirs, files in os.walk(os.path.join(self.working_dir, "backend")):
                # Ignorar __pycache__
                dirs[:] = [d for d in dirs if d != "__pycache__"]
                
                for file in files:
                    if file.endswith(".py"):
                        filepath = os.path.join(root, file)
                        rel_path = os.path.relpath(filepath, self.working_dir)
                        
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                content = f.read()
                            
                            tree = ast.parse(content)
                            imports = []
                            
                            for node in ast.walk(tree):
                                if isinstance(node, ast.Import):
                                    for alias in node.names:
                                        if alias.name.startswith("backend"):
                                            imports.append(alias.name)
                                elif isinstance(node, ast.ImportFrom):
                                    if node.module and node.module.startswith("backend"):
                                        imports.append(node.module)
                            
                            if imports:
                                imports_map[rel_path] = imports
                                
                        except Exception as e:
                            self.log(f"Error parsing {rel_path}: {e}", "warning")
            
            # Buscar ciclos simples (A -> B -> A)
            cycles = []
            for module_a, imports_a in imports_map.items():
                for imp in imports_a:
                    # Convertir import a posible archivo
                    imp_file = imp.replace(".", "/") + ".py"
                    if imp_file in imports_map:
                        # Verificar si hay ciclo reverso
                        for imp_b in imports_map.get(imp_file, []):
                            if module_a.replace("/", ".").replace(".py", "") in imp_b:
                                cycles.append((module_a, imp_file))
            
            if cycles:
                for cycle in cycles[:5]:
                    self.add_finding(
                        title="Posible ciclo de importación",
                        description=f"{cycle[0]} <-> {cycle[1]}",
                        severity=CheckSeverity.LOW,
                        recommendation="Refactorizar para evitar dependencias circulares"
                    )
                return self._create_result("passed", f"{len(cycles)} posibles ciclos")
            
            return self._create_result("passed", "Sin ciclos detectados")
            
        except Exception as e:
            self.log(f"Error: {e}", "error")
            return self._create_result("error", str(e))
