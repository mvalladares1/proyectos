"""
Módulo de clasificación de cuentas para Flujo de Caja.
Maneja el mapeo y clasificación de cuentas contables a conceptos NIIF IAS 7.
"""
from typing import Dict, List, Optional, Tuple
import json
import os


class ClasificadorCuentas:
    """Clasifica cuentas contables según conceptos NIIF IAS 7."""
    
    def __init__(self, catalogo: Dict, mapeo: Dict):
        """
        Args:
            catalogo: Catálogo de conceptos NIIF
            mapeo: Mapeo actual de cuentas a conceptos
        """
        self.catalogo = catalogo
        self.mapeo = mapeo
        self._migracion_codigos = catalogo.get("migracion_codigos", {})
    
    def _migrar_codigo_antiguo(self, codigo_antiguo: str) -> str:
        """Migra códigos antiguos a nuevos usando el diccionario de migración."""
        return self._migracion_codigos.get(codigo_antiguo, codigo_antiguo)
    
    def clasificar_cuenta_explicita(self, codigo_cuenta: str) -> Tuple[str, bool]:
        """
        Clasifica una cuenta usando el mapeo explícito.
        
        Args:
            codigo_cuenta: Código de la cuenta contable
            
        Returns:
            Tuple (concepto_id, es_explicito)
        """
        from .constants import CONCEPTO_FALLBACK, CATEGORIA_UNCLASSIFIED
        
        # Buscar en mapeo explícito
        cuenta_info = self.mapeo.get(codigo_cuenta)
        if cuenta_info:
            concepto_raw = cuenta_info.get('concepto', '')
            # Migrar si es necesario
            concepto_id = self._migrar_codigo_antiguo(concepto_raw)
            if concepto_id and concepto_id != CATEGORIA_UNCLASSIFIED:
                return concepto_id, True
        
        # No encontrado
        return CONCEPTO_FALLBACK, False
    
    def clasificar_cuenta(self, codigo_cuenta: str) -> Tuple[str, bool]:
        """
        Clasifica una cuenta (primero explícito, luego inferencia).
        
        Args:
            codigo_cuenta: Código de la cuenta contable
            
        Returns:
            Tuple (concepto_id, es_explicito)
        """
        # Primero intentar mapeo explícito
        concepto, es_explicito = self.clasificar_cuenta_explicita(codigo_cuenta)
        if es_explicito:
            return concepto, True
        
        # Si no está mapeado, retornar fallback
        return concepto, False
    
    def guardar_mapeo_cuenta(self, codigo: str, concepto_id: str, nombre: str = "", 
                            comentario: str = "", mapeo_path: str = None) -> bool:
        """
        Guarda un mapeo de cuenta en el archivo JSON.
        
        Args:
            codigo: Código de la cuenta
            concepto_id: ID del concepto NIIF
            nombre: Nombre de la cuenta
            comentario: Comentario adicional
            mapeo_path: Ruta al archivo de mapeo
            
        Returns:
            True si se guardó correctamente
        """
        try:
            # Actualizar mapeo en memoria
            self.mapeo[codigo] = {
                'concepto': concepto_id,
                'nombre': nombre,
                'comentario': comentario
            }
            
            # Guardar a archivo si se proporcionó la ruta
            if mapeo_path:
                with open(mapeo_path, 'w', encoding='utf-8') as f:
                    json.dump(self.mapeo, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"[ClasificadorCuentas] Error guardando mapeo: {e}")
            return False
    
    def eliminar_mapeo_cuenta(self, codigo: str, mapeo_path: str = None) -> bool:
        """
        Elimina un mapeo de cuenta.
        
        Args:
            codigo: Código de la cuenta a eliminar
            mapeo_path: Ruta al archivo de mapeo
            
        Returns:
            True si se eliminó correctamente
        """
        try:
            if codigo in self.mapeo:
                del self.mapeo[codigo]
                
                # Guardar a archivo si se proporcionó la ruta
                if mapeo_path:
                    with open(mapeo_path, 'w', encoding='utf-8') as f:
                        json.dump(self.mapeo, f, indent=2, ensure_ascii=False)
                
                return True
            return False
        except Exception as e:
            print(f"[ClasificadorCuentas] Error eliminando mapeo: {e}")
            return False
    
    def sugerir_categoria_por_prefijo(self, codigo: str, nombre: str = "") -> str:
        """
        Sugiere una categoría basada en el prefijo del código contable.
        
        Args:
            codigo: Código de la cuenta
            nombre: Nombre de la cuenta (opcional)
            
        Returns:
            Sugerencia de categoría
        """
        prefijo = codigo[:2] if len(codigo) >= 2 else codigo
        
        # Activos
        if prefijo.startswith('1'):
            if prefijo.startswith('11'):
                if prefijo in ['110', '111']:
                    return "Efectivo (cuentas especiales)"
                else:
                    return "OP01 - Clientes o cobros comerciales"
            elif prefijo.startswith('12'):
                return "IN03 - PPE o activo fijo"
            elif prefijo.startswith('13') or prefijo.startswith('14'):
                return "IN01/IN02 - Inversiones"
            else:
                return "Verificar - Activo"
        
        # Pasivos
        elif prefijo.startswith('2'):
            if prefijo in ['210', '211', '212']:
                return "OP02 - Proveedores"
            elif prefijo in ['215', '216', '217']:
                return "OP03 - Remuneraciones o OP06 - Impuestos"
            elif prefijo.startswith('22') or prefijo.startswith('23'):
                return "FI01/FI02 - Préstamos"
            else:
                return "Verificar - Pasivo"
        
        # Patrimonio
        elif prefijo.startswith('3'):
            return "FI07 - Patrimonio/Dividendos"
        
        # Ingresos
        elif prefijo.startswith('4'):
            if prefijo in ['410', '411', '412']:
                return "OP01 - Ingresos"
            else:
                return "OP05 - Otros ingresos"
        
        # Costos
        elif prefijo.startswith('5'):
            return "OP02 - Costos/Gastos operacionales"
        
        # Gastos
        elif prefijo.startswith('6'):
            if prefijo in ['620', '621', '622', '623']:
                return "OP03 - Remuneraciones"
            elif prefijo in ['650', '651']:
                return "OP04 - Intereses pagados"
            elif prefijo in ['640', '641']:
                return "OP06 - Impuestos"
            else:
                return "OP07 - Otros gastos operacionales"
        
        return "Verificar - Categoría desconocida"
