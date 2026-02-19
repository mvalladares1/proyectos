"""
BUENOBOT - Permissions Checks

Checks de permisos y control de acceso:
- Validación de roles
- Fugas de permisos
- Consistencia de permissions.json
"""
import json
import os
from typing import Dict, List, Any, Set

from .base import BaseCheck, CheckRegistry
from ..models import CheckResult, CheckCategory, CheckSeverity


@CheckRegistry.register("permissions_check", quick=True, full=True)
class PermissionsCheck(BaseCheck):
    """Check de consistencia del sistema de permisos"""
    
    name = "Permissions System"
    category = CheckCategory.PERMISSIONS
    description = "Verifica consistencia del archivo de permisos y su uso"
    
    async def run(self) -> CheckResult:
        self.log("Verificando sistema de permisos...")
        
        issues = []
        
        # 1. Cargar permissions.json
        permissions_path = os.path.join(self.working_dir, "data", "permissions.json")
        
        try:
            with open(permissions_path, 'r', encoding='utf-8') as f:
                permissions_data = json.load(f)
        except FileNotFoundError:
            self.add_finding(
                title="permissions.json no encontrado",
                description=f"El archivo {permissions_path} no existe",
                severity=CheckSeverity.CRITICAL,
                recommendation="Crear archivo data/permissions.json"
            )
            return self._create_result("failed", "permissions.json no existe")
        except json.JSONDecodeError as e:
            self.add_finding(
                title="permissions.json inválido",
                description=f"Error de JSON: {e}",
                severity=CheckSeverity.CRITICAL
            )
            return self._create_result("failed", "permissions.json malformado")
        
        # 2. Verificar estructura
        defined_permissions = self._extract_defined_permissions(permissions_data)
        self.log(f"Permisos definidos: {len(defined_permissions)}")
        
        # 3. Buscar permisos usados en código
        used_permissions = await self._find_used_permissions()
        self.log(f"Permisos usados en código: {len(used_permissions)}")
        
        # 4. Comparar
        # Permisos usados pero no definidos
        undefined = used_permissions - defined_permissions
        for perm in undefined:
            issues.append({
                "type": "undefined",
                "permission": perm,
                "severity": CheckSeverity.MEDIUM
            })
            self.add_finding(
                title=f"Permiso no definido: {perm}",
                description=f"El permiso '{perm}' se usa en código pero no está en permissions.json",
                severity=CheckSeverity.MEDIUM,
                recommendation=f"Agregar '{perm}' a permissions.json"
            )
        
        # Permisos definidos pero no usados (warning menor)
        unused = defined_permissions - used_permissions
        if len(unused) > 5:  # Solo alertar si hay muchos
            self.add_finding(
                title=f"{len(unused)} permisos sin usar",
                description=f"Permisos definidos pero no encontrados en código: {', '.join(list(unused)[:5])}...",
                severity=CheckSeverity.INFO
            )
        
        # 5. Verificar estructura de usuarios
        users = permissions_data.get("users", {})
        admin_count = 0
        
        for email, user_data in users.items():
            # Verificar que los permisos del usuario existan
            user_perms = user_data.get("permissions", [])
            for perm in user_perms:
                if perm not in defined_permissions and perm != "*":
                    self.add_finding(
                        title=f"Permiso inválido asignado",
                        description=f"Usuario {email} tiene permiso '{perm}' que no existe",
                        severity=CheckSeverity.MEDIUM
                    )
            
            # Contar admins
            if user_data.get("role") == "admin" or "*" in user_perms:
                admin_count += 1
        
        self.log(f"Usuarios con rol admin: {admin_count}")
        
        # 6. Verificar que no hay permisos sensibles expuestos
        sensitive_patterns = ["admin", "delete", "write", "full_access"]
        for perm in defined_permissions:
            if any(pattern in perm.lower() for pattern in sensitive_patterns):
                self.log(f"Permiso sensible encontrado: {perm}")
        
        # Resultado
        critical_issues = len([i for i in issues if i.get("severity") == CheckSeverity.HIGH])
        
        if critical_issues > 0:
            return self._create_result("failed", f"{len(issues)} problemas de permisos")
        elif len(undefined) > 0:
            return self._create_result("passed", f"{len(undefined)} permisos sin definir (warning)")
        
        return self._create_result("passed", f"{len(defined_permissions)} permisos OK")
    
    def _extract_defined_permissions(self, data: Dict[str, Any]) -> Set[str]:
        """Extrae todos los permisos definidos del JSON"""
        permissions = set()
        
        # Buscar en 'available_permissions' o similar
        if "available_permissions" in data:
            for perm in data["available_permissions"]:
                if isinstance(perm, str):
                    permissions.add(perm)
                elif isinstance(perm, dict):
                    permissions.add(perm.get("id", perm.get("name", "")))
        
        # Buscar en estructura de módulos
        if "modules" in data:
            for module_name, module_data in data.get("modules", {}).items():
                if isinstance(module_data, dict):
                    for tab_name in module_data.get("tabs", {}).keys():
                        permissions.add(f"{module_name}.{tab_name}")
        
        # Buscar permisos en usuarios (los que están asignados)
        for user_data in data.get("users", {}).values():
            for perm in user_data.get("permissions", []):
                if perm != "*":
                    permissions.add(perm)
        
        return permissions
    
    async def _find_used_permissions(self) -> Set[str]:
        """Busca permisos usados en el código"""
        used = set()
        
        # Patrones de uso de permisos
        patterns = [
            r'tiene_acceso_pagina\(["\']([^"\']+)["\']\)',
            r'tiene_permiso\(["\']([^"\']+)["\']\)',
            r'check_permission\(["\']([^"\']+)["\']\)',
            r'required_permission\s*=\s*["\']([^"\']+)["\']',
            r'permission\s*=\s*["\']([^"\']+)["\']',
        ]
        
        import re
        
        search_dirs = ["pages", "backend/routers"]
        
        for search_dir in search_dirs:
            dir_path = os.path.join(self.working_dir, search_dir)
            if not os.path.exists(dir_path):
                continue
            
            for root, dirs, files in os.walk(dir_path):
                dirs[:] = [d for d in dirs if d != "__pycache__"]
                
                for file in files:
                    if not file.endswith(".py"):
                        continue
                    
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        for pattern in patterns:
                            matches = re.findall(pattern, content)
                            used.update(matches)
                    except Exception:
                        continue
        
        return used


@CheckRegistry.register("role_leak_check", quick=True, full=True)
class RoleLeakCheck(BaseCheck):
    """Check de fugas de permisos por roles"""
    
    name = "Role Leak Detection"
    category = CheckCategory.PERMISSIONS
    description = "Detecta posibles fugas donde se omite validación de permisos"
    
    async def run(self) -> CheckResult:
        self.log("Buscando fugas de permisos...")
        
        leaks = []
        
        # Buscar páginas Streamlit sin proteger_pagina()
        pages_dir = os.path.join(self.working_dir, "pages")
        
        for root, dirs, files in os.walk(pages_dir):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            
            for file in files:
                if not file.endswith(".py"):
                    continue
                if file.startswith("__"):
                    continue
                
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, self.working_dir)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Verificar que tenga protección
                    has_protection = any([
                        "proteger_pagina()" in content,
                        "proteger_pagina(" in content,
                        "# No requiere autenticación" in content,
                        "# Public page" in content,
                    ])
                    
                    # Si es un archivo de página principal (número_nombre.py)
                    import re
                    if re.match(r'^\d+_', file) and not has_protection:
                        leaks.append({
                            "file": rel_path,
                            "issue": "Página sin proteger_pagina()"
                        })
                        self.add_finding(
                            title="Página sin protección de autenticación",
                            description=f"{rel_path} no llama a proteger_pagina()",
                            severity=CheckSeverity.HIGH,
                            location=rel_path,
                            recommendation="Agregar proteger_pagina() al inicio de la página"
                        )
                    
                    # Verificar consultas Odoo sin validación
                    if "odoo_client" in content or "execute_kw" in content:
                        if "allowed_company_ids" not in content and "company_id" not in content:
                            # Puede ser OK dependiendo del caso
                            self.log(f"? {rel_path} - Consulta Odoo sin filtro de company explícito")
                    
                except Exception as e:
                    self.log(f"Error leyendo {rel_path}: {e}", "warning")
        
        if leaks:
            return self._create_result(
                "failed",
                f"{len(leaks)} páginas sin protección"
            )
        
        return self._create_result("passed", "Todas las páginas protegidas")
