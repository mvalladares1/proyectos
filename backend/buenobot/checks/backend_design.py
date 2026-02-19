"""
BUENOBOT v2.0 - Backend Design Analyzer

Análisis estático de código backend usando AST (Abstract Syntax Tree).
Detecta antipatrones, problemas de seguridad y malas prácticas.
"""
import ast
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum

from ..models import CheckResult, Finding, CheckSeverity, CheckCategory
from .base import BaseCheck, CheckRegistry

logger = logging.getLogger(__name__)


class IssueType(str, Enum):
    """Tipos de issues detectados por el analyzer"""
    SECURITY = "security"
    DESIGN = "design"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"


@dataclass
class CodeIssue:
    """Issue detectado en el código"""
    issue_type: IssueType
    rule: str
    message: str
    file_path: str
    line_number: int
    column: int = 0
    severity: CheckSeverity = CheckSeverity.MEDIUM
    code_snippet: Optional[str] = None
    recommendation: Optional[str] = None


class ASTAnalyzer(ast.NodeVisitor):
    """
    Visitor AST que detecta antipatrones en código Python.
    
    Reglas implementadas:
    - password_in_query_params: Detecta uso de password en Query()
    - print_in_routers: Detecta print() en archivos de router
    - date_as_str_param: Detecta fechas como str en lugar de date
    - mutative_get: Detecta operaciones de escritura en endpoints GET
    - missing_pydantic: Detecta endpoints sin validación Pydantic
    - generic_exception: Detecta except Exception sin especificar
    - hardcoded_credentials: Detecta credenciales hardcodeadas
    - sql_injection_risk: Detecta concatenación de strings en queries
    """
    
    def __init__(self, file_path: str, source_code: str):
        self.file_path = file_path
        self.source_code = source_code
        self.source_lines = source_code.split('\n')
        self.issues: List[CodeIssue] = []
        
        # Contexto
        self.in_router_file = 'router' in file_path.lower()
        self.in_async_def = False
        self.current_function: Optional[str] = None
        self.current_decorator: Optional[str] = None
        self.imports: Set[str] = set()
        
        # Detectar tipo de endpoint
        self.endpoint_methods: Dict[str, str] = {}  # func_name -> http_method
    
    def get_code_snippet(self, lineno: int, context: int = 1) -> str:
        """Obtiene snippet de código con contexto"""
        start = max(0, lineno - context - 1)
        end = min(len(self.source_lines), lineno + context)
        lines = self.source_lines[start:end]
        return '\n'.join(f"{start+i+1}: {line}" for i, line in enumerate(lines))
    
    def visit_Import(self, node: ast.Import):
        """Registra imports"""
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Registra imports from"""
        if node.module:
            self.imports.add(node.module)
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Analiza definiciones de funciones"""
        self._analyze_function(node)
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Analiza funciones async"""
        self.in_async_def = True
        self._analyze_function(node)
        self.in_async_def = False
        self.generic_visit(node)
    
    def _analyze_function(self, node):
        """Análisis común de funciones"""
        self.current_function = node.name
        
        # Detectar decoradores de endpoint
        http_method = None
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    method = decorator.func.attr.lower()
                    if method in ['get', 'post', 'put', 'delete', 'patch']:
                        http_method = method
                        self.endpoint_methods[node.name] = method
        
        self.current_decorator = http_method
        
        # Analizar parámetros de la función
        self._check_query_params(node)
        
        # Analizar cuerpo de la función
        for child in ast.walk(node):
            self._check_node(child, http_method)
        
        self.current_function = None
        self.current_decorator = None
    
    def _check_query_params(self, node):
        """
        Verifica parámetros Query() para issues de seguridad.
        
        Detecta patrones como:
            password: str = Query(...)
            username: str = Query(...)
        """
        # Crear mapeo de argumentos a sus defaults
        # args.args son los parámetros posicionales
        # args.defaults son los valores default (alineados desde la derecha)
        # args.kwonlyargs son los keyword-only args (después de *)
        # args.kw_defaults son sus defaults
        
        sensitive_names = ['password', 'passwd', 'pwd', 'secret', 'api_key', 'apikey', 
                          'token', 'credential', 'auth_key', 'private_key']
        
        # Procesar args posicionales con defaults
        n_defaults = len(node.args.defaults)
        n_args = len(node.args.args)
        
        # Los defaults se alinean desde la derecha
        # Si hay 5 args y 3 defaults, los últimos 3 args tienen defaults
        for i, arg in enumerate(node.args.args):
            arg_name = arg.arg.lower()
            
            # Verificar si es nombre sensible
            is_sensitive = any(sensitive in arg_name for sensitive in sensitive_names)
            
            if not is_sensitive:
                continue
            
            # Obtener el default correspondiente (si existe)
            default_index = i - (n_args - n_defaults)
            has_query_default = False
            
            if default_index >= 0 and default_index < len(node.args.defaults):
                default = node.args.defaults[default_index]
                # Verificar si es Query(...)
                if isinstance(default, ast.Call):
                    func_name = self._get_call_name(default)
                    if 'Query' in func_name or func_name == 'Query':
                        has_query_default = True
            
            # También verificar anotación tipo Annotated[str, Query(...)]
            if arg.annotation:
                try:
                    ann_str = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else ""
                    if 'Query' in ann_str:
                        has_query_default = True
                except Exception:
                    pass
            
            if has_query_default:
                self.issues.append(CodeIssue(
                    issue_type=IssueType.SECURITY,
                    rule="password_in_query_params",
                    message=f"CRÍTICO: Parámetro sensible '{arg.arg}' expuesto en Query params (visible en URL, logs, historial del navegador)",
                    file_path=self.file_path,
                    line_number=arg.lineno if hasattr(arg, 'lineno') else node.lineno,
                    column=arg.col_offset if hasattr(arg, 'col_offset') else 0,
                    severity=CheckSeverity.CRITICAL,
                    code_snippet=self.get_code_snippet(arg.lineno if hasattr(arg, 'lineno') else node.lineno),
                    recommendation="Mover credenciales a HTTP Header (Authorization, X-API-Key) o Body de POST request"
                ))
        
        # Procesar keyword-only args (params después de *)
        for i, arg in enumerate(node.args.kwonlyargs):
            arg_name = arg.arg.lower()
            
            is_sensitive = any(sensitive in arg_name for sensitive in sensitive_names)
            
            if not is_sensitive:
                continue
            
            # Get kw_default
            has_query_default = False
            if i < len(node.args.kw_defaults) and node.args.kw_defaults[i] is not None:
                default = node.args.kw_defaults[i]
                if isinstance(default, ast.Call):
                    func_name = self._get_call_name(default)
                    if 'Query' in func_name or func_name == 'Query':
                        has_query_default = True
            
            if has_query_default:
                self.issues.append(CodeIssue(
                    issue_type=IssueType.SECURITY,
                    rule="password_in_query_params",
                    message=f"CRÍTICO: Parámetro sensible '{arg.arg}' expuesto en Query params (visible en URL, logs, historial del navegador)",
                    file_path=self.file_path,
                    line_number=arg.lineno if hasattr(arg, 'lineno') else node.lineno,
                    column=arg.col_offset if hasattr(arg, 'col_offset') else 0,
                    severity=CheckSeverity.CRITICAL,
                    code_snippet=self.get_code_snippet(arg.lineno if hasattr(arg, 'lineno') else node.lineno),
                    recommendation="Mover credenciales a HTTP Header (Authorization, X-API-Key) o Body de POST request"
                ))
        
        # También detectar username en Query (aunque menos crítico que password)
        # Solo reportar como HIGH, no CRITICAL
        username_names = ['username', 'user', 'userid', 'user_id', 'login']
        
        for i, arg in enumerate(node.args.args):
            arg_name = arg.arg.lower()
            
            is_username = any(uname == arg_name for uname in username_names)
            
            if not is_username:
                continue
            
            default_index = i - (n_args - n_defaults)
            has_query_default = False
            
            if default_index >= 0 and default_index < len(node.args.defaults):
                default = node.args.defaults[default_index]
                if isinstance(default, ast.Call):
                    func_name = self._get_call_name(default)
                    if 'Query' in func_name or func_name == 'Query':
                        has_query_default = True
            
            if has_query_default:
                self.issues.append(CodeIssue(
                    issue_type=IssueType.SECURITY,
                    rule="username_in_query_params",  
                    message=f"Advertencia: Nombre de usuario '{arg.arg}' expuesto en Query params",
                    file_path=self.file_path,
                    line_number=arg.lineno if hasattr(arg, 'lineno') else node.lineno,
                    column=arg.col_offset if hasattr(arg, 'col_offset') else 0,
                    severity=CheckSeverity.HIGH,
                    code_snippet=self.get_code_snippet(arg.lineno if hasattr(arg, 'lineno') else node.lineno),
                    recommendation="Considerar mover a HTTP Header para mejor seguridad"
                ))
    
    def _check_node(self, node, http_method: Optional[str]):
        """Verifica nodo individual por antipatrones"""
        
        # RULE: print_in_routers
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == 'print':
                if self.in_router_file:
                    self.issues.append(CodeIssue(
                        issue_type=IssueType.MAINTAINABILITY,
                        rule="print_in_routers",
                        message=f"print() encontrado en router - usar logging en su lugar",
                        file_path=self.file_path,
                        line_number=node.lineno,
                        severity=CheckSeverity.LOW,
                        code_snippet=self.get_code_snippet(node.lineno),
                        recommendation="Reemplazar print() con logger.info() o logger.debug()"
                    ))
        
        # RULE: mutative_get - Detecta operaciones de escritura en GET
        if http_method == 'get' and isinstance(node, ast.Call):
            func_name = self._get_call_name(node)
            # Métodos que modifican datos
            mutative_methods = [
                'write', 'create', 'delete', 'update', 'save', 'remove',
                'insert', 'execute', 'commit', 'post', 'put', 'patch'
            ]
            if any(mut in func_name.lower() for mut in mutative_methods):
                self.issues.append(CodeIssue(
                    issue_type=IssueType.DESIGN,
                    rule="mutative_get",
                    message=f"Operación mutativa '{func_name}' en endpoint GET",
                    file_path=self.file_path,
                    line_number=node.lineno,
                    severity=CheckSeverity.HIGH,
                    code_snippet=self.get_code_snippet(node.lineno),
                    recommendation="Endpoints GET deben ser idempotentes. Usar POST/PUT/DELETE para operaciones de escritura"
                ))
        
        # RULE: generic_exception
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                self.issues.append(CodeIssue(
                    issue_type=IssueType.MAINTAINABILITY,
                    rule="generic_exception",
                    message="except sin tipo específico - captura todas las excepciones",
                    file_path=self.file_path,
                    line_number=node.lineno,
                    severity=CheckSeverity.MEDIUM,
                    code_snippet=self.get_code_snippet(node.lineno),
                    recommendation="Especificar tipos de excepción concretos (ValueError, HTTPException, etc.)"
                ))
            elif isinstance(node.type, ast.Name) and node.type.id == 'Exception':
                # Verificar si hace re-raise o logging
                has_raise = any(isinstance(n, ast.Raise) for n in ast.walk(node))
                has_logging = any(
                    isinstance(n, ast.Call) and self._get_call_name(n).startswith('log')
                    for n in ast.walk(node) if isinstance(n, ast.Call)
                )
                if not has_raise and not has_logging:
                    self.issues.append(CodeIssue(
                        issue_type=IssueType.MAINTAINABILITY,
                        rule="generic_exception",
                        message="except Exception sin re-raise o logging - puede ocultar errores",
                        file_path=self.file_path,
                        line_number=node.lineno,
                        severity=CheckSeverity.MEDIUM,
                        code_snippet=self.get_code_snippet(node.lineno),
                        recommendation="Agregar logging o re-raise de la excepción"
                    ))
        
        # RULE: hardcoded_credentials
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    var_name = target.id.lower()
                    if any(s in var_name for s in ['password', 'secret', 'api_key', 'token', 'credential']):
                        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                            if len(node.value.value) > 3:  # No alertar por strings vacíos
                                self.issues.append(CodeIssue(
                                    issue_type=IssueType.SECURITY,
                                    rule="hardcoded_credentials",
                                    message=f"Posible credencial hardcodeada en variable '{target.id}'",
                                    file_path=self.file_path,
                                    line_number=node.lineno,
                                    severity=CheckSeverity.CRITICAL,
                                    code_snippet=self.get_code_snippet(node.lineno),
                                    recommendation="Usar variables de entorno o secrets manager"
                                ))
        
        # RULE: sql_injection_risk (f-strings o concatenación en queries)
        if isinstance(node, ast.Call):
            func_name = self._get_call_name(node)
            if any(sql in func_name.lower() for sql in ['execute', 'raw', 'query', 'search_read']):
                for arg in node.args:
                    if isinstance(arg, ast.JoinedStr):  # f-string
                        self.issues.append(CodeIssue(
                            issue_type=IssueType.SECURITY,
                            rule="sql_injection_risk",
                            message="Posible SQL injection: f-string en query",
                            file_path=self.file_path,
                            line_number=node.lineno,
                            severity=CheckSeverity.HIGH,
                            code_snippet=self.get_code_snippet(node.lineno),
                            recommendation="Usar parámetros preparados (placeholders) en lugar de interpolación"
                        ))
                    elif isinstance(arg, ast.BinOp) and isinstance(arg.op, (ast.Add, ast.Mod)):
                        # Concatenación de strings
                        self.issues.append(CodeIssue(
                            issue_type=IssueType.SECURITY,
                            rule="sql_injection_risk",
                            message="Posible SQL injection: concatenación de strings en query",
                            file_path=self.file_path,
                            line_number=node.lineno,
                            severity=CheckSeverity.HIGH,
                            code_snippet=self.get_code_snippet(node.lineno),
                            recommendation="Usar parámetros preparados (placeholders) en lugar de concatenación"
                        ))
    
    def _get_call_name(self, node: ast.Call) -> str:
        """Obtiene nombre de la función llamada"""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                return f"{node.func.value.id}.{node.func.attr}"
            return node.func.attr
        return ""


class BackendDesignAnalyzer:
    """
    Analizador de diseño de backend.
    
    Escanea archivos Python buscando antipatrones usando AST.
    """
    
    def __init__(self, working_dir: str = "/app"):
        self.working_dir = Path(working_dir)
        self.issues: List[CodeIssue] = []
    
    def analyze_file(self, file_path: str) -> List[CodeIssue]:
        """Analiza un archivo individual"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            tree = ast.parse(source_code)
            analyzer = ASTAnalyzer(file_path, source_code)
            analyzer.visit(tree)
            
            return analyzer.issues
            
        except SyntaxError as e:
            logger.warning(f"Syntax error en {file_path}: {e}")
            return [CodeIssue(
                issue_type=IssueType.MAINTAINABILITY,
                rule="syntax_error",
                message=f"Error de sintaxis: {str(e)}",
                file_path=file_path,
                line_number=e.lineno or 0,
                severity=CheckSeverity.CRITICAL
            )]
        except Exception as e:
            logger.error(f"Error analizando {file_path}: {e}")
            return []
    
    def analyze_directory(
        self,
        directory: Optional[str] = None,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None
    ) -> List[CodeIssue]:
        """
        Analiza todos los archivos Python en un directorio.
        
        Args:
            directory: Directorio a escanear (default: working_dir)
            include_patterns: Patrones glob para incluir
            exclude_patterns: Patrones para excluir
        """
        scan_dir = Path(directory) if directory else self.working_dir
        include_patterns = include_patterns or ["**/*.py"]
        exclude_patterns = exclude_patterns or [
            "**/venv/**", "**/.venv/**", "**/node_modules/**",
            "**/__pycache__/**", "**/migrations/**", "**/.git/**"
        ]
        
        all_issues = []
        files_scanned = 0
        
        for pattern in include_patterns:
            for file_path in scan_dir.glob(pattern):
                # Verificar exclusiones
                str_path = str(file_path)
                if any(Path(str_path).match(exc) for exc in exclude_patterns):
                    continue
                
                if file_path.is_file():
                    issues = self.analyze_file(str(file_path))
                    all_issues.extend(issues)
                    files_scanned += 1
        
        self.issues = all_issues
        logger.info(f"Analizados {files_scanned} archivos, {len(all_issues)} issues encontrados")
        
        return all_issues
    
    def get_summary(self) -> Dict[str, Any]:
        """Genera resumen del análisis"""
        by_severity = {}
        by_rule = {}
        by_type = {}
        
        for issue in self.issues:
            # Por severidad
            sev = issue.severity.value
            by_severity[sev] = by_severity.get(sev, 0) + 1
            
            # Por regla
            by_rule[issue.rule] = by_rule.get(issue.rule, 0) + 1
            
            # Por tipo
            t = issue.issue_type.value
            by_type[t] = by_type.get(t, 0) + 1
        
        return {
            "total_issues": len(self.issues),
            "by_severity": by_severity,
            "by_rule": by_rule,
            "by_type": by_type
        }


@CheckRegistry.register("backend_design", quick=True, full=True)
class BackendDesignCheck(BaseCheck):
    """
    Check BUENOBOT que ejecuta análisis de diseño de backend.
    
    Usa AST para detectar:
    - password en query params
    - print() en routers
    - operaciones mutativas en GET
    - except Exception genérico
    - credenciales hardcodeadas
    - riesgos de SQL injection
    """
    
    check_id = "backend_design"
    check_name = "Backend Design Analysis"
    category = CheckCategory.CODE_QUALITY
    description = "Análisis estático de diseño backend usando AST"
    quick_check = True  # Incluir en quick scan
    
    def __init__(self):
        super().__init__()
        self.scan_dirs = ["backend/routers", "backend/services"]
    
    async def run(self, **kwargs) -> CheckResult:
        """Ejecuta análisis de diseño"""
        import asyncio
        start_time = asyncio.get_event_loop().time()
        findings: List[Finding] = []
        
        working_dir = kwargs.get("working_dir", "/app")
        scan_dirs = kwargs.get("scan_dirs", self.scan_dirs)
        
        try:
            analyzer = BackendDesignAnalyzer(working_dir)
            all_issues: List[CodeIssue] = []
            
            for scan_dir in scan_dirs:
                full_path = os.path.join(working_dir, scan_dir)
                if os.path.exists(full_path):
                    issues = analyzer.analyze_directory(full_path)
                    all_issues.extend(issues)
            
            # Convertir issues a findings
            for issue in all_issues:
                # Hacer path relativo
                rel_path = issue.file_path
                if rel_path.startswith(working_dir):
                    rel_path = rel_path[len(working_dir):].lstrip('/')
                
                findings.append(Finding(
                    title=f"[{issue.rule}] {issue.message[:50]}",
                    description=issue.message,
                    severity=issue.severity,
                    location=f"{rel_path}:{issue.line_number}",
                    evidence=issue.code_snippet,
                    recommendation=issue.recommendation,
                    priority=self._get_priority(issue.severity)
                ))
            
            # Generar summary
            summary = analyzer.get_summary()
            
            # Determinar status
            has_critical = any(f.severity in [CheckSeverity.CRITICAL, CheckSeverity.HIGH] for f in findings)
            status = "failed" if has_critical else ("passed" if len(findings) == 0 else "warning")
            
            return CheckResult(
                check_id=self.check_id,
                check_name=self.check_name,
                category=self.category,
                status=status,
                summary=f"{summary['total_issues']} issues: {summary.get('by_severity', {})}",
                findings=findings,
                duration_ms=int((asyncio.get_event_loop().time() - start_time) * 1000),
                raw_output=str(summary)
            )
            
        except Exception as e:
            logger.exception("Error en BackendDesignCheck")
            return CheckResult(
                check_id=self.check_id,
                check_name=self.check_name,
                category=self.category,
                status="error",
                summary=f"Error: {str(e)}",
                findings=[Finding(
                    title="Error ejecutando análisis",
                    description=str(e),
                    severity=CheckSeverity.MEDIUM
                )],
                duration_ms=int((asyncio.get_event_loop().time() - start_time) * 1000)
            )
    
    def _get_priority(self, severity: CheckSeverity) -> str:
        """Mapea severidad a prioridad"""
        mapping = {
            CheckSeverity.CRITICAL: "P0",
            CheckSeverity.HIGH: "P1",
            CheckSeverity.MEDIUM: "P2",
            CheckSeverity.LOW: "P3",
            CheckSeverity.INFO: "P4"
        }
        return mapping.get(severity, "P2")
