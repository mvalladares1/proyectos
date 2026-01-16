"""
Servicio de Flujo de Caja - Estado de Flujo de Efectivo NIIF IAS 7 (Método Directo)

Este servicio genera el Estado de Flujo de Efectivo obteniendo datos desde Odoo.
El flujo se construye exclusivamente desde movimientos que afectan cuentas de efectivo.
Usa el catálogo oficial de conceptos NIIF para clasificación.

REFACTORIZADO: Constantes y helpers extraídos a módulos separados.
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import os

from shared.odoo_client import OdooClient

# Importar desde módulos modularizados
from .flujo_caja.constants import (
    CONCEPTO_FALLBACK,
    ESTRUCTURA_FLUJO,
    CUENTAS_FIJAS_FINANCIAMIENTO,
    CATEGORIA_NEUTRAL,
    CATEGORIA_PENDIENTE,
    CATEGORIA_UNCLASSIFIED,
    CATEGORIA_FX_EFFECT,
    EMOJIS_ACTIVIDAD
)
from .flujo_caja.helpers import (
    sumar_hijos,
    migrar_codigo_antiguo,
    build_categorias_dropdown,
    aggregate_montos_by_concepto
)


class FlujoCajaService:
    """Servicio para generar Estado de Flujo de Efectivo NIIF IAS 7."""
    
    def __init__(self, username: str = None, password: str = None):
        self.username = username
        self.password = password
        self._odoo = None
        self.catalogo = self._cargar_catalogo()
        self.mapeo_cuentas = self._cargar_mapeo()
        self.cuentas_monitoreadas = self._cargar_cuentas_monitoreadas()
        self._cache_cuentas_efectivo = None
        self._migracion_codigos = self.catalogo.get("migracion_codigos", {})
    
    @property
    def odoo(self):
        """Lazy initialization de OdooClient."""
        if self._odoo is None:
            self._odoo = OdooClient(username=self.username, password=self.password)
        return self._odoo
    
    def _get_catalogo_path(self) -> str:
        """Retorna la ruta al archivo de catálogo."""
        return os.path.join(
            os.path.dirname(__file__), 
            '..', 'data', 'catalogo_conceptos.json'
        )
    
    def _get_mapeo_path(self) -> str:
        """Retorna la ruta al archivo de mapeo."""
        return os.path.join(
            os.path.dirname(__file__), 
            '..', 'data', 'mapeo_cuentas.json'
        )
    
    def _get_cuentas_monitoreadas_path(self) -> str:
        """Retorna la ruta al archivo de cuentas monitoreadas."""
        return os.path.join(
            os.path.dirname(__file__), 
            '..', 'data', 'cuentas_monitoreadas.json'
        )
    
    def _cargar_cuentas_monitoreadas(self) -> Dict:
        """Carga la configuración de cuentas monitoreadas (estáticas)."""
        path = self._get_cuentas_monitoreadas_path()
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"[FlujoCaja] Error cargando cuentas monitoreadas: {e}")
        return {"cuentas_efectivo": {"codigos": [], "prefijos": ["110", "111"]}, "cuentas_contrapartida": {"codigos": []}}
    
    def _cargar_catalogo(self) -> Dict:
        """Carga el catálogo oficial de conceptos NIIF."""
        catalogo_path = self._get_catalogo_path()
        try:
            if os.path.exists(catalogo_path):
                with open(catalogo_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"[FlujoCaja] Error cargando catálogo: {e}")
        return {"conceptos": [], "migracion_codigos": {}}
    
    def _cargar_mapeo(self) -> Dict:
        """Carga el mapeo de cuentas desde archivo JSON."""
        mapeo_path = self._get_mapeo_path()
        try:
            if os.path.exists(mapeo_path):
                with open(mapeo_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"[FlujoCaja] Error cargando mapeo: {e}")
        
        return self._mapeo_default()
    
    def _mapeo_default(self) -> Dict:
        """Retorna mapeo por defecto (estructura vacía para forzar clasificación explícita)."""
        return {
            "version": "3.0",
            "cuentas_efectivo": {
                "efectivo": {"prefijos": ["110", "111"], "codigos_incluir": [], "codigos_excluir": []},
                "equivalentes": {"prefijos": [], "codigos_incluir": [], "codigos_excluir": []}
            },
            "mapeo_cuentas": {},
            "configuracion": {
                "modo_estricto": False,
                "bloquear_si_no_clasificado": False
            }
        }
    
    def get_catalogo_conceptos(self) -> List[Dict]:
        """Retorna la lista de conceptos del catálogo oficial."""
        return self.catalogo.get("conceptos", [])
    
    def get_concepto_por_id(self, concepto_id: str) -> Optional[Dict]:
        """Busca un concepto por su ID."""
        for c in self.catalogo.get("conceptos", []):
            if c.get("id") == concepto_id:
                return c
        return None
    
    def build_ias7_catalog_operation(self) -> List[Dict]:
        """
        Retorna solo los conceptos de OPERACION ordenados por 'order'.
        Útil para renderizar el árbol de títulos IAS 7.
        """
        conceptos = self.catalogo.get("conceptos", [])
        operacion = [c for c in conceptos if c.get("actividad") == "OPERACION"]
        return sorted(operacion, key=lambda x: x.get("order", 999))
    
    def build_ias7_catalog_by_activity(self, actividad: str = None) -> List[Dict]:
        """
        Retorna conceptos filtrados por actividad ordenados por 'order'.
        Si actividad es None, retorna TODO el catálogo ordenado.
        """
        conceptos = self.catalogo.get("conceptos", [])
        if actividad:
            filtered = [c for c in conceptos if c.get("actividad") == actividad.upper()]
        else:
            filtered = conceptos
        return sorted(filtered, key=lambda x: x.get("order", 999))
    
    def aggregate_by_ias7(self, montos_por_linea: Dict[str, float], 
                          proyeccion_por_linea: Dict[str, float] = None,
                          modo: str = "consolidado") -> List[Dict]:
        """
        Motor de agregación IAS 7 (delegado a helpers).
        
        Toma montos de LINEAs y calcula HEADERs/TOTALs automáticamente.
        """
        conceptos = self.catalogo.get("conceptos", [])
        return aggregate_montos_by_concepto(conceptos, montos_por_linea, proyeccion_por_linea, modo)
    
    def _sumar_hijos(self, parent_id: str, montos: Dict[str, float], conceptos: List[Dict]) -> float:
        """Delegado a helpers.sumar_hijos."""
        return sumar_hijos(parent_id, montos, conceptos)
    
    def get_categorias_ias7_dropdown(self) -> List[Dict]:
        """Delegado a helpers.build_categorias_dropdown."""
        conceptos = self.catalogo.get("conceptos", [])
        return build_categorias_dropdown(conceptos, EMOJIS_ACTIVIDAD)
        
        # Agregar NEUTRAL al final
        
        return resultado
    
    def _migrar_codigo_antiguo(self, codigo_antiguo: str) -> str:
        """Delegado a helpers.migrar_codigo_antiguo."""
        return migrar_codigo_antiguo(codigo_antiguo, self._migracion_codigos)
    
    def _clasificar_cuenta_explicita(self, codigo_cuenta: str) -> Tuple[str, bool]:
        """
        Clasifica una cuenta usando mapeo explícito por código.
        Retorna (concepto_id, es_pendiente).
        """
        # 1. Chequear mapeo OBLIGATORIO (Financiamiento)
        if codigo_cuenta in CUENTAS_FIJAS_FINANCIAMIENTO:
            return (CUENTAS_FIJAS_FINANCIAMIENTO[codigo_cuenta], False)

        mapeo = self.mapeo_cuentas.get("mapeo_cuentas", {})
        
        # Search exact code
        if codigo_cuenta in mapeo:
            cuenta_info = mapeo[codigo_cuenta]
            if isinstance(cuenta_info, dict):
                # Nuevo formato: {"concepto_id": "1.2.1"}
                concepto_id = cuenta_info.get("concepto_id")
                if concepto_id:
                    return (concepto_id, False)
                
                # Formato antiguo: {"categoria": "OP02"}
                categoria = cuenta_info.get("categoria")
                if categoria:
                    # Migrar código antiguo a nuevo
                    nuevo_id = self._migrar_codigo_antiguo(categoria)
                    return (nuevo_id, False)
            elif isinstance(cuenta_info, str):
                # Formato legacy simple: "OP01"
                nuevo_id = self._migrar_codigo_antiguo(cuenta_info)
                return (nuevo_id, False)
        
        # No mapeada → ignorar (retornar None para que se salte)
        return (None, True)
    
    def _clasificar_cuenta(self, codigo_cuenta: str) -> Tuple[str, bool]:
        """
        Clasifica una cuenta usando mapeo explícito.
        Wrapper que mantiene compatibilidad.
        Retorna (concepto_id, es_pendiente).
        """
        return self._clasificar_cuenta_explicita(codigo_cuenta)
    
    def guardar_mapeo_cuenta(self, codigo: str, concepto_id: str, nombre: str = "", 
                                usuario: str = "system", impacto_estimado: float = None) -> bool:
        """Guarda o actualiza el mapeo de una cuenta individual con audit trail."""
        mapeo_path = self._get_mapeo_path()
        try:
            # Cargar mapeo actual
            mapeo = self._cargar_mapeo()
            
            # Obtener concepto_id anterior para audit
            concepto_anterior = None
            if "mapeo_cuentas" in mapeo and codigo in mapeo["mapeo_cuentas"]:
                cuenta_ant = mapeo["mapeo_cuentas"][codigo]
                if isinstance(cuenta_ant, dict):
                    concepto_anterior = cuenta_ant.get("concepto_id") or cuenta_ant.get("categoria")
                elif isinstance(cuenta_ant, str):
                    concepto_anterior = cuenta_ant
            
            # Actualizar cuenta con nuevo formato
            if "mapeo_cuentas" not in mapeo:
                mapeo["mapeo_cuentas"] = {}
            
            mapeo["mapeo_cuentas"][codigo] = {
                "concepto_id": concepto_id,  # Nuevo formato oficial
                "nombre": nombre,
                "fecha_asignacion": datetime.now().isoformat(),
                "usuario": usuario
            }
            
            # Agregar a historial de cambios (audit trail)
            if "historial_cambios" not in mapeo:
                mapeo["historial_cambios"] = []
            
            mapeo["historial_cambios"].append({
                "fecha": datetime.now().isoformat(),
                "usuario": usuario,
                "accion": "actualizar" if concepto_anterior else "crear",
                "cuenta": codigo,
                "nombre_cuenta": nombre,
                "concepto_anterior": concepto_anterior,
                "concepto_nuevo": concepto_id,
                "impacto_estimado": impacto_estimado
            })
            
            # Limitar historial a últimos 500 cambios
            if len(mapeo["historial_cambios"]) > 500:
                mapeo["historial_cambios"] = mapeo["historial_cambios"][-500:]
            
            # Guardar
            with open(mapeo_path, 'w', encoding='utf-8') as f:
                json.dump(mapeo, f, indent=2, ensure_ascii=False)
            
            # Actualizar cache
            self.mapeo_cuentas = mapeo
            return True
        except Exception as e:
            print(f"[FlujoCaja] Error guardando mapeo cuenta: {e}")
            return False
    
    def eliminar_mapeo_cuenta(self, codigo: str) -> bool:
        """Elimina el mapeo de una cuenta."""
        mapeo_path = self._get_mapeo_path()
        try:
            mapeo = self._cargar_mapeo()
            if codigo in mapeo.get("mapeo_cuentas", {}):
                del mapeo["mapeo_cuentas"][codigo]
                with open(mapeo_path, 'w', encoding='utf-8') as f:
                    json.dump(mapeo, f, indent=2, ensure_ascii=False)
                self.mapeo_cuentas = mapeo
            return True
        except Exception as e:
            print(f"[FlujoCaja] Error eliminando mapeo: {e}")
            return False
    
    def guardar_mapeo(self, mapeo: Dict) -> bool:
        """Guarda el mapeo completo en archivo JSON."""
        mapeo_path = self._get_mapeo_path()
        try:
            os.makedirs(os.path.dirname(mapeo_path), exist_ok=True)
            with open(mapeo_path, 'w', encoding='utf-8') as f:
                json.dump(mapeo, f, indent=2, ensure_ascii=False)
            self.mapeo_cuentas = mapeo
            return True
        except Exception as e:
            print(f"[FlujoCaja] Error guardando mapeo: {e}")
            return False

    def reset_mapeo(self) -> bool:
        """
        Resetea COMPLETAMENTE el mapeo de cuentas (excepto configuración técnica).
        Usado para empezar desde cero.
        """
        try:
            mapeo_actual = self._cargar_mapeo()
            # Restaurar a default pero manteniendo ciertas configuraciones si existen?
            # El usuario pidió "desde 0", así que volvemos a la estructura por defecto.
            nuevo_mapeo = self._mapeo_default()
            
            # (Opcional) Guardar backup antes de borrar?
            # No solicitado, pero buena práctica. Por ahora solo reseteamos.
            
            # Mantener configuración si existe, solo borrar mapeos de cuentas
            if "configuracion" in mapeo_actual:
                 nuevo_mapeo["configuracion"] = mapeo_actual["configuracion"]
            
            if "cuentas_efectivo" in mapeo_actual:
                 # Mantener cuentas de efectivo sería útil para no reconfigurar todo lo técnico
                 # Pero si quieren "desde 0", asumiremos solo borrar clasificaciones del mapeo
                 nuevo_mapeo["cuentas_efectivo"] = mapeo_actual["cuentas_efectivo"]

            return self.guardar_mapeo(nuevo_mapeo)
        except Exception as e:
             print(f"[FlujoCaja] Error reseteando mapeo: {e}")
             return False

    
    def get_configuracion(self) -> Dict:
        """Retorna la configuración del mapeo."""
        return self.mapeo_cuentas.get("configuracion", {
            "modo_estricto": False,
            "bloquear_si_no_clasificado": False,
            "umbral_alerta_no_clasificado": 0.05
        })
    
    def validar_flujo(self, flujos_por_linea: Dict, 
                      efectivo_inicial: float, efectivo_final_calculado: float,
                      flujos_por_actividad: Dict = None,
                      efectivo_final_real: float = None) -> Dict:
        """
        Valida el flujo según reglas financieras (v2.2).
        
        Validaciones:
        1. NEUTRAL debe ser ~0
        2. UNCLASSIFIED por actividad (umbrales separados)
        3. Signo esperado (alertas informativas, no errores)
        4. Reconciliación
        """
        config = self.get_configuracion()
        categorias = self.mapeo_cuentas.get("categorias", {})
        alertas = []
        errores = []
        info = []  # Alertas informativas (signo)
        
        neutral = flujos_por_linea.get(CATEGORIA_NEUTRAL, 0)
        sin_clasificar = flujos_por_linea.get(CATEGORIA_UNCLASSIFIED, 0)
        
        # 1. Validar NEUTRAL (~0)
        if abs(neutral) > 1000:
            alertas.append({
                "tipo": "NEUTRAL_NO_CERO",
                "mensaje": f"NEUTRAL debería ser ~$0, pero es ${neutral:,.0f}",
                "impacto": neutral
            })
        
        # 2. Validar UNCLASSIFIED por actividad
        umbrales = config.get("umbrales_unclassified", {
            "operacion": 0.05, "inversion": 0.10, "financiamiento": 0.10
        })
        
        if flujos_por_actividad and sin_clasificar != 0:
            # Calcular proporción por actividad (simplificado: usamos total)
            for act_key, umbral in [
                ("OPERACION", umbrales.get("operacion", 0.05)),
                ("INVERSION", umbrales.get("inversion", 0.10)),
                ("FINANCIAMIENTO", umbrales.get("financiamiento", 0.10))
            ]:
                act_total = abs(flujos_por_actividad.get(act_key, {}).get("subtotal", 0))
                if act_total > 0:
                    # Proporción de sin_clasificar vs total de la actividad
                    proporcion = abs(sin_clasificar) / (act_total + abs(sin_clasificar))
                    if proporcion > umbral:
                        alertas.append({
                            "tipo": f"UNCLASSIFIED_{act_key}",
                            "mensaje": f"{proporcion*100:.1f}% sin clasificar afecta {act_key}",
                            "umbral": umbral,
                            "proporcion": proporcion
                        })
                        break  # Una alerta es suficiente
        elif sin_clasificar != 0:
            # Fallback: validación global
            total_flujos = sum(abs(v) for k, v in flujos_por_linea.items() if k != CATEGORIA_NEUTRAL)
            if total_flujos > 0:
                proporcion = abs(sin_clasificar) / total_flujos
                if proporcion > 0.05:
                    nivel = "error" if config.get("modo_estricto") else "warning"
                    msg = {
                        "tipo": "UNCLASSIFIED_ALTO",
                        "mensaje": f"{proporcion*100:.1f}% sin clasificar (${abs(sin_clasificar):,.0f})",
                        "impacto": sin_clasificar
                    }
                    (errores if nivel == "error" else alertas).append(msg)
        
        # 3. Validar signo esperado (INFORMATIVO, no bloqueante)
        if config.get("alertar_signo_inesperado", True):
            for codigo, monto in flujos_por_linea.items():
                if monto == 0 or codigo in [CATEGORIA_NEUTRAL, CATEGORIA_UNCLASSIFIED, CATEGORIA_FX_EFFECT]:
                    continue
                cat_info = categorias.get(codigo, {})
                signo_esperado = cat_info.get("signo_esperado", "variable")
                
                if signo_esperado == "positivo" and monto < 0:
                    info.append({
                        "tipo": "SIGNO_INESPERADO",
                        "mensaje": f"{codigo} es negativo (${monto:,.0f}), se esperaba positivo",
                        "codigo": codigo
                    })
                elif signo_esperado == "negativo" and monto > 0:
                    info.append({
                        "tipo": "SIGNO_INESPERADO",
                        "mensaje": f"{codigo} es positivo (${monto:,.0f}), se esperaba negativo",
                        "codigo": codigo
                    })
        
        # 4. Reconciliación
        if efectivo_final_real is not None:
            diferencia = efectivo_final_calculado - efectivo_final_real
            if abs(diferencia) > 100:
                alertas.append({
                    "tipo": "RECONCILIACION_DIFERENCIA",
                    "mensaje": f"Diferencia de ${diferencia:,.0f} entre calculado y real",
                    "diferencia": diferencia
                })
        
        es_valido = len(errores) == 0
        bloquear = config.get("bloquear_si_no_clasificado", False) and not es_valido
        
        return {
            "valido": es_valido,
            "bloquear_visualizacion": bloquear,
            "alertas": alertas,
            "errores": errores,
            "info": info,
            "modo_estricto": config.get("modo_estricto", False)
        }
    
    def _get_cuentas_efectivo(self) -> List[int]:
        """
        Obtiene IDs de cuentas de efectivo y equivalentes.
        
        Lógica de override: codigos_excluir > codigos_incluir > prefijos
        """
        if self._cache_cuentas_efectivo:
            return self._cache_cuentas_efectivo
        
        cuentas_efectivo_config = self.mapeo_cuentas.get("cuentas_efectivo", {})
        
        # Recopilar todos los prefijos, incluir y excluir de ambos tipos
        all_prefijos = []
        all_incluir = []
        all_excluir = []
        
        for tipo in ["efectivo", "equivalentes"]:
            tipo_config = cuentas_efectivo_config.get(tipo, {})
            all_prefijos.extend(tipo_config.get("prefijos", []))
            all_incluir.extend(tipo_config.get("codigos_incluir", []))
            all_excluir.extend(tipo_config.get("codigos_excluir", []))
        
        # Fallback para estructura anterior
        if not all_prefijos and "prefijos" in cuentas_efectivo_config:
            all_prefijos = cuentas_efectivo_config.get("prefijos", ["110", "111"])
        
        if not all_prefijos:
            all_prefijos = ["110", "111"]
        
        # Construir dominio OR para prefijos
        domain = ['|'] * (len(all_prefijos) - 1) if len(all_prefijos) > 1 else []
        for prefijo in all_prefijos:
            domain.append(['code', '=like', f'{prefijo}%'])
        
        try:
            cuentas = self.odoo.search_read(
                'account.account',
                domain,
                ['id', 'code', 'name'],
                limit=200
            )
            
            # Aplicar lógica de override: excluir > incluir > prefijos
            resultado_ids = []
            codigos_encontrados = set()
            
            for c in cuentas:
                codigo = c.get('code', '')
                # Excluir tiene prioridad máxima
                if codigo in all_excluir:
                    continue
                resultado_ids.append(c['id'])
                codigos_encontrados.add(codigo)
            
            # Agregar codigos_incluir que no fueron encontrados por prefijo
            # (necesitan búsqueda adicional)
            codigos_faltantes = [c for c in all_incluir if c not in codigos_encontrados]
            if codigos_faltantes:
                try:
                    cuentas_extra = self.odoo.search_read(
                        'account.account',
                        [['code', 'in', codigos_faltantes]],
                        ['id', 'code'],
                        limit=50
                    )
                    for c in cuentas_extra:
                        if c.get('code') not in all_excluir:
                            resultado_ids.append(c['id'])
                except:
                    pass
            
            self._cache_cuentas_efectivo = resultado_ids
            return self._cache_cuentas_efectivo
        except Exception as e:
            print(f"[FlujoCaja] Error obteniendo cuentas efectivo: {e}")
            return []
    
    def _clasificar_cuenta(self, codigo_cuenta: str) -> str:
        """
        Clasifica una cuenta usando mapeo explícito por código.
        Prioriza mapeo explícito, retorna UNCLASSIFIED si no está mapeada.
        """
        return self._clasificar_cuenta_explicita(codigo_cuenta)
    
    def _get_saldo_efectivo(self, fecha: str, cuentas_efectivo_ids: List[int]) -> float:
        """Calcula el saldo de efectivo a una fecha dada usando agregación."""
        if not cuentas_efectivo_ids:
            return 0.0
        
        try:
            # OPTIMIZADO: Usar read_group para agregar en servidor en vez de traer todas las líneas
            result = self.odoo.models.execute_kw(
                self.odoo.db, self.odoo.uid, self.odoo.password,
                'account.move.line', 'read_group',
                [[
                    ['account_id', 'in', cuentas_efectivo_ids],
                    ['parent_state', '=', 'posted'],
                    ['date', '<=', fecha]
                ]],
                {'fields': ['balance:sum'], 'groupby': [], 'lazy': False}
            )
            
            if result and len(result) > 0:
                return result[0].get('balance', 0) or 0.0
            return 0.0
        except Exception as e:
            # Fallback al método anterior si read_group no está disponible
            print(f"[FlujoCaja] read_group failed, using fallback: {e}")
            try:
                moves = self.odoo.search_read(
                    'account.move.line',
                    [
                        ['account_id', 'in', cuentas_efectivo_ids],
                        ['parent_state', '=', 'posted'],
                        ['date', '<=', fecha]
                    ],
                    ['balance'],
                    limit=50000
                )
                return sum(m.get('balance', 0) for m in moves)
            except:
                return 0.0
    
    def get_flujo_mensualizado(self, fecha_inicio: str, fecha_fin: str, company_id=None, agrupacion='mensual') -> Dict:
        """
        Genera el Estado de Flujo de Efectivo con granularidad MENSUAL.
        
        Similar a get_flujo_efectivo pero agrupa los datos por mes usando
        read_group con 'date:month' para obtener montos reales por período.
        
        Returns:
            {
                "meses": ["2026-01", "2026-02", ...],
                "actividades": {
                    "OPERACION": {
                        "subtotal_por_mes": {"2026-01": 1000, ...},
                        "conceptos": [
                            {"id": "1.1.1", "nombre": "Ventas", "montos_por_mes": {...}, "total": 5000}
                        ]
                    }
                },
                "efectivo_por_mes": {"2026-01": {"inicial": X, "final": Y}, ...}
            }
        """
        from datetime import datetime
        from calendar import monthrange
        
        resultado = {
            "meta": {"version": "3.2", "mode": "mensualizado"},
            "periodo": {"inicio": fecha_inicio, "fin": fecha_fin},
            "generado": datetime.now().isoformat(),
            "meses": [],
            "actividades": {},
            "conciliacion": {},
            "efectivo_por_mes": {}
        }
        
        # 1. Generar lista de meses en el rango
        fecha_ini_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d')
        fecha_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d')
        
        meses_lista = []
        
        if agrupacion == 'semanal':
            # Generar semanas ISO (YYYY-Www)
            from datetime import timedelta
            current = fecha_ini_dt
            while current <= fecha_fin_dt:
                y, w, d = current.isocalendar()
                periodo_str = f"{y}-W{w:02d}"
                if periodo_str not in meses_lista:
                    meses_lista.append(periodo_str)
                current += timedelta(days=1)
        else:
            # Generar meses (YYYY-MM)
            current = fecha_ini_dt.replace(day=1)
            while current <= fecha_fin_dt:
                mes_str = current.strftime("%Y-%m")
                meses_lista.append(mes_str)
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1)
                else:
                    current = current.replace(month=current.month + 1)
        
        resultado["meses"] = meses_lista
        
        # 2. Obtener cuentas de efectivo
        cuentas_efectivo_ids = self._get_cuentas_efectivo()
        if not cuentas_efectivo_ids:
            resultado["error"] = "No se encontraron cuentas de efectivo configuradas"
            return resultado
            
        # Helper para manejar agrupación
        groupby_key = 'date:week' if agrupacion == 'semanal' else 'date:month'
        
        def get_periodo_from_odoo(val):
            """Convierte valor de Odoo (W01 2026 o January 2026) a formato (2026-W01 o 2026-01)"""
            if not val: return None
            if agrupacion == 'semanal':
                # Odoo return "W01 2026"
                try:
                    parts = val.split(' ')
                    if len(parts) == 2:
                        week_str = parts[0] # W01
                        year_str = parts[1] # 2026
                        return f"{year_str}-{week_str}"
                except:
                    pass
                return val
            else:
                return self._parse_odoo_month(val)
        
        # 3. Efectivo inicial (día anterior al inicio)
        fecha_anterior = (fecha_ini_dt - timedelta(days=1)).strftime('%Y-%m-%d')
        efectivo_inicial_global = self._get_saldo_efectivo(fecha_anterior, cuentas_efectivo_ids)
        resultado["conciliacion"]["efectivo_inicial"] = round(efectivo_inicial_global, 0)
        
        # 4. Obtener IDs de movimientos de efectivo (posted + draft para proyección)
        # Incluimos 'draft' para capturar facturas/asientos en borrador como proyección
        domain = [
            ['account_id', 'in', cuentas_efectivo_ids],
            ['parent_state', 'in', ['posted', 'draft']],  # INCLUYE BORRADORES
            ['date', '>=', fecha_inicio],
            ['date', '<=', fecha_fin]
        ]
        if company_id:
            domain.append(['company_id', '=', company_id])
        
        try:
            movimientos_efectivo = self.odoo.search_read(
                'account.move.line',
                domain,
                ['move_id'],
                limit=50000
            )
        except Exception as e:
            resultado["error"] = f"Error obteniendo movimientos: {e}"
            return resultado
        
        asientos_ids = list(set(
            m['move_id'][0] if isinstance(m.get('move_id'), (list, tuple)) else m.get('move_id')
            for m in movimientos_efectivo if m.get('move_id')
        ))
        
        if not asientos_ids:
            # No hay movimientos, devolver estructura vacía
            for act_key in ["OPERACION", "INVERSION", "FINANCIAMIENTO"]:
                resultado["actividades"][act_key] = {
                    "nombre": self._get_actividad_nombre(act_key),
                    "subtotal_por_mes": {m: 0 for m in meses_lista},
                    "subtotal": 0,
                    "conceptos": []
                }
            return resultado
        
        # 5. AGREGACIÓN POR MES Y CUENTA: read_group con date:month
        # Estructura: montos_por_concepto_mes[concepto_id][mes] = monto
        montos_por_concepto_mes = {}
        
        # Inicializar con categorías del catálogo
        for c in self.catalogo.get("conceptos", []):
            if c.get("tipo") == "LINEA":
                montos_por_concepto_mes[c["id"]] = {m: 0.0 for m in meses_lista}
        montos_por_concepto_mes[CATEGORIA_NEUTRAL] = {m: 0.0 for m in meses_lista}
        
        # Diccionario para tracking de cuentas individuales por concepto (para drill-down)
        # Estructura: {concepto_id: {codigo_cuenta: {nombre, monto, cantidad, etiquetas: {name: monto}}}}
        cuentas_por_concepto = {}

        
        # Procesar en chunks
        chunk_size = 5000
        for i in range(0, len(asientos_ids), chunk_size):
            chunk_asientos = asientos_ids[i:i + chunk_size]
            
            try:
                # read_group con agrupación por cuenta Y mes
                grupos = self.odoo.models.execute_kw(
                    self.odoo.db, self.odoo.uid, self.odoo.password,
                    'account.move.line', 'read_group',
                    [[
                        ['move_id', 'in', chunk_asientos],
                        ['account_id', 'not in', cuentas_efectivo_ids]
                    ]],
                    {
                        'fields': ['balance', 'account_id', 'date'], 
                        'groupby': ['account_id', groupby_key],
                        'lazy': False
                    }
                )
                
                # Obtener lista de cuentas monitoreadas
                cuentas_monitoreadas = self.cuentas_monitoreadas.get("cuentas_contrapartida", {}).get("codigos", [])
                filtrar_monitoreadas = len(cuentas_monitoreadas) > 0
                
                for grupo in grupos:
                    acc_data = grupo.get('account_id')
                    balance = grupo.get('balance', 0)
                    periodo_val = grupo.get(groupby_key, '')
                    
                    if not acc_data or not periodo_val:
                        continue
                    
                    # Parsear
                    mes_str = get_periodo_from_odoo(periodo_val)
                    if not mes_str:
                        print(f"[FlujoCaja WARNING] No se pudo parsear mes: '{date_month}'")
                        continue
                    if mes_str not in meses_lista:
                        # El mes está fuera del rango solicitado
                        continue
                    
                    acc_display = acc_data[1] if len(acc_data) > 1 else "Unknown"
                    codigo_cuenta = acc_display.split(' ')[0] if ' ' in acc_display else acc_display
                    
                    # Aplicar filtro de cuentas monitoreadas
                    if filtrar_monitoreadas and codigo_cuenta not in cuentas_monitoreadas:
                        continue
                    
                    # Clasificar cuenta
                    concepto_id, es_pendiente = self._clasificar_cuenta(codigo_cuenta)
                    
                    if concepto_id is None:
                        continue
                    
                    # Acumular monto en el concepto y mes correspondiente
                    if concepto_id not in montos_por_concepto_mes:
                        montos_por_concepto_mes[concepto_id] = {m: 0.0 for m in meses_lista}
                    
                    montos_por_concepto_mes[concepto_id][mes_str] += balance
                    
                    # Trackear cuenta individual para drill-down
                    if concepto_id not in cuentas_por_concepto:
                        cuentas_por_concepto[concepto_id] = {}
                    if codigo_cuenta not in cuentas_por_concepto[concepto_id]:
                        nombre_cuenta = acc_display.split(' ', 1)[1] if ' ' in acc_display else acc_display
                        cuentas_por_concepto[concepto_id][codigo_cuenta] = {
                            'nombre': nombre_cuenta[:50],
                            'monto': 0.0,
                            'cantidad': 0,
                            'montos_por_mes': {m: 0.0 for m in meses_lista},
                            'etiquetas': {},  # {name_etiqueta: monto}
                            'account_id': acc_data[0] if acc_data else None  # Guardar ID para consulta posterior
                        }
                    cuentas_por_concepto[concepto_id][codigo_cuenta]['monto'] += balance
                    cuentas_por_concepto[concepto_id][codigo_cuenta]['cantidad'] += 1
                    if mes_str in meses_lista:
                        cuentas_por_concepto[concepto_id][codigo_cuenta]['montos_por_mes'][mes_str] += balance

                    
            except Exception as e:
                print(f"[FlujoCaja] Error en agregación mensual: {e}")
        
        # 5a. ETIQUETAS POR CUENTA CON MONTOS POR MES: Obtener campo 'name' agrupado por cuenta y mes
        # Esto permite ver el desglose como: Concepto → Cuenta → Etiqueta (ej: Leasing Generador) con montos por mes
        try:
            # Recopilar todos los account_ids que tenemos en cuentas_por_concepto
            account_ids_to_query = set()
            for concepto_id, cuentas in cuentas_por_concepto.items():
                for codigo, cuenta_data in cuentas.items():
                    if cuenta_data.get('account_id'):
                        account_ids_to_query.add(cuenta_data['account_id'])
            
            if account_ids_to_query:
                print(f"[FlujoCaja] Obteniendo etiquetas con montos por mes para {len(account_ids_to_query)} cuentas...")
                
                # read_group agrupando por account_id, name (etiqueta) Y date:month
                grupos_etiquetas = self.odoo.models.execute_kw(
                    self.odoo.db, self.odoo.uid, self.odoo.password,
                    'account.move.line', 'read_group',
                    [[
                        ['move_id', 'in', asientos_ids],
                        ['account_id', 'in', list(account_ids_to_query)]
                    ]],
                    {
                        'fields': ['balance', 'account_id', 'name', 'date'],
                        'groupby': ['account_id', 'name', groupby_key],
                        'lazy': False
                    }
                )
                
                print(f"[FlujoCaja] Grupos de etiquetas con mes obtenidos: {len(grupos_etiquetas)}")
                
                # Crear un mapeo account_id → codigo_cuenta para asociar
                account_id_to_codigo = {}
                for concepto_id, cuentas in cuentas_por_concepto.items():
                    for codigo, cuenta_data in cuentas.items():
                        if cuenta_data.get('account_id'):
                            account_id_to_codigo[cuenta_data['account_id']] = (concepto_id, codigo)
                
                # Procesar grupos y agregar etiquetas a las cuentas
                # Ahora cada grupo tiene account_id, name, date:month y balance
                for grupo in grupos_etiquetas:
                    acc_data = grupo.get('account_id')
                    etiqueta_name = grupo.get('name', '')
                    balance = grupo.get('balance', 0)
                    periodo_val = grupo.get(groupby_key, '')
                    
                    if not acc_data or not etiqueta_name:
                        continue
                    
                    account_id = acc_data[0] if isinstance(acc_data, (list, tuple)) else acc_data
                    
                    # Parsear mes
                    mes_str = get_periodo_from_odoo(periodo_val)
                    
                    if account_id in account_id_to_codigo:
                        concepto_id, codigo_cuenta = account_id_to_codigo[account_id]
                        
                        # Agregar etiqueta al diccionario de la cuenta
                        if 'etiquetas' not in cuentas_por_concepto[concepto_id][codigo_cuenta]:
                            cuentas_por_concepto[concepto_id][codigo_cuenta]['etiquetas'] = {}
                        
                        # Limpiar nombre de etiqueta (truncar si es muy largo)
                        etiqueta_limpia = str(etiqueta_name)[:60].strip() if etiqueta_name else "Sin etiqueta"
                        
                        # Inicializar estructura de etiqueta si no existe
                        if etiqueta_limpia not in cuentas_por_concepto[concepto_id][codigo_cuenta]['etiquetas']:
                            cuentas_por_concepto[concepto_id][codigo_cuenta]['etiquetas'][etiqueta_limpia] = {
                                'monto': 0.0,
                                'montos_por_mes': {m: 0.0 for m in meses_lista}
                            }
                        
                        # Sumar al monto total
                        cuentas_por_concepto[concepto_id][codigo_cuenta]['etiquetas'][etiqueta_limpia]['monto'] += balance
                        
                        # Sumar al monto del mes correspondiente
                        if mes_str and mes_str in meses_lista:
                            cuentas_por_concepto[concepto_id][codigo_cuenta]['etiquetas'][etiqueta_limpia]['montos_por_mes'][mes_str] += balance
                
                print(f"[FlujoCaja] Etiquetas con montos por mes procesadas correctamente")
                
        except Exception as e:
            print(f"[FlujoCaja] Error obteniendo etiquetas: {e}")
            import traceback
            traceback.print_exc()

        
        # 5b. PROYECCIÓN: Interpretar facturas en borrador como movimientos futuros de efectivo
        # Para cada factura draft, obtenemos sus líneas y clasificamos según las cuentas contables
        try:
            facturas_draft = self.odoo.search_read(
                'account.move',
                [
                    ['state', '=', 'draft'],
                    ['move_type', 'in', ['out_invoice', 'in_invoice', 'out_refund', 'in_refund']],
                    ['date', '>=', fecha_inicio],   # CAMBIO: Usar fecha contable ('date') en vez de invoice_date
                    ['date', '<=', fecha_fin]
                ],
                ['id', 'move_type', 'invoice_date', 'invoice_date_due', 'line_ids'],
                limit=5000
            )
            
            print(f"[FlujoCaja] Facturas draft encontradas: {len(facturas_draft)}")
            
            if facturas_draft:
                # Obtener todos los IDs de líneas de todas las facturas draft
                all_line_ids = []
                factura_por_linea = {}  # Para mapear línea → factura
                for factura in facturas_draft:
                    line_ids = factura.get('line_ids', [])
                    for lid in line_ids:
                        all_line_ids.append(lid)
                        factura_por_linea[lid] = factura
                
                if all_line_ids:
                    # Obtener las líneas con sus cuentas contables
                    lineas = self.odoo.search_read(
                        'account.move.line',
                        [['id', 'in', all_line_ids]],
                        ['id', 'account_id', 'balance', 'debit', 'credit', 'move_id', 'name'],
                        limit=50000
                    )
                    
                    for linea in lineas:
                        linea_id = linea.get('id')
                        factura = factura_por_linea.get(linea_id)
                        if not factura:
                            continue
                        
                        # Determinar mes de la proyección
                        fecha_proy = factura.get('invoice_date_due') or factura.get('invoice_date')
                        # Fallback a date (fecha contable) si no hay fecha factura
                        if not fecha_proy:
                            fecha_proy = factura.get('date') # Asegurar que esto venga en la factura arriba, o usar el metodo corregido antes

                        if not fecha_proy:
                            continue
                        
                        try:
                            fecha_dt = datetime.strptime(str(fecha_proy), '%Y-%m-%d')
                            if agrupacion == 'semanal':
                                y, w, d = fecha_dt.isocalendar()
                                mes_proy = f"{y}-W{w:02d}"
                            else:
                                mes_proy = fecha_dt.strftime('%Y-%m')
                        except:
                            continue
                        
                        if mes_proy not in meses_lista:
                            continue
                        
                        # Obtener código de cuenta contable
                        acc_data = linea.get('account_id')
                        if not acc_data:
                            continue
                        
                        acc_display = acc_data[1] if len(acc_data) > 1 else "Unknown"
                        codigo_cuenta = acc_display.split(' ')[0] if ' ' in acc_display else acc_display
                        
                        # Excluir cuentas de efectivo (ya las manejamos en flujo real)
                        if codigo_cuenta.startswith('110') or codigo_cuenta.startswith('111'):
                            continue
                        
                        # Clasificar usando el mapeo existente
                        concepto_id, es_pendiente = self._clasificar_cuenta(codigo_cuenta)
                        
                        if concepto_id is None or concepto_id == CATEGORIA_NEUTRAL:
                            continue
                        
                        # Determinar signo según tipo de factura
                        move_type = factura.get('move_type', '')
                        balance = linea.get('balance', 0)
                        
                        # Invertir signo: el balance de account.move.line es desde perspectiva contable
                        # Para flujo de caja proyectado, interpretamos como movimiento de efectivo
                        if move_type in ['out_invoice', 'out_refund']:
                            monto_efectivo = -balance
                        else:
                            monto_efectivo = balance
                        
                        # Agregar a montos por concepto
                        if concepto_id not in montos_por_concepto_mes:
                            montos_por_concepto_mes[concepto_id] = {m: 0.0 for m in meses_lista}
                        
                        montos_por_concepto_mes[concepto_id][mes_proy] += monto_efectivo
                        
                        # Trackear cuenta para drill-down (facturas draft)
                        if concepto_id not in cuentas_por_concepto:
                            cuentas_por_concepto[concepto_id] = {}
                        if codigo_cuenta not in cuentas_por_concepto[concepto_id]:
                            nombre_cuenta = acc_display.split(' ', 1)[1] if ' ' in acc_display else acc_display
                            # Inicializar cuenta
                            cuentas_por_concepto[concepto_id][codigo_cuenta] = {
                                'nombre': nombre_cuenta[:50],
                                'monto': 0.0,
                                'cantidad': 0,
                                'account_id': acc_data[0], # Guardar account_id por si acaso
                                'montos_por_mes': {m: 0.0 for m in meses_lista},
                                'etiquetas': {} # Importante inicializar etiquetas
                            }
                        
                        # Asegurar que existan etiquetas (si la cuenta venía de antes sin etiquetas)
                        if 'etiquetas' not in cuentas_por_concepto[concepto_id][codigo_cuenta]:
                            cuentas_por_concepto[concepto_id][codigo_cuenta]['etiquetas'] = {}
                            
                        # Actualizar métricas de cuenta
                        cuentas_por_concepto[concepto_id][codigo_cuenta]['monto'] += monto_efectivo
                        cuentas_por_concepto[concepto_id][codigo_cuenta]['cantidad'] += 1
                        if mes_proy in meses_lista:
                            cuentas_por_concepto[concepto_id][codigo_cuenta]['montos_por_mes'][mes_proy] += monto_efectivo
                            
                        # === AGREGAR PROCESAMIENTO DE ETIQUETA (campo 'name' de la línea) ===
                        etiqueta_raw = linea.get('name', '')
                        etiqueta_limpia = str(etiqueta_raw)[:60].strip() if etiqueta_raw else "Sin etiqueta"
                        
                        # Normalizar un poco para evitar duplicados por espacios
                        # Nota: no hacemos lower() completo porque queremos conservar formato, pero sí strip()
                        
                        if etiqueta_limpia not in cuentas_por_concepto[concepto_id][codigo_cuenta]['etiquetas']:
                            cuentas_por_concepto[concepto_id][codigo_cuenta]['etiquetas'][etiqueta_limpia] = {
                                'monto': 0.0,
                                'montos_por_mes': {m: 0.0 for m in meses_lista}
                            }
                        elif isinstance(cuentas_por_concepto[concepto_id][codigo_cuenta]['etiquetas'][etiqueta_limpia], float):
                             # Migrar formato antiguo (solo float) a nuevo (dict) si es necesario (defensivo)
                             val_ant = cuentas_por_concepto[concepto_id][codigo_cuenta]['etiquetas'][etiqueta_limpia]
                             cuentas_por_concepto[concepto_id][codigo_cuenta]['etiquetas'][etiqueta_limpia] = {
                                'monto': val_ant,
                                'montos_por_mes': {m: 0.0 for m in meses_lista}
                            }
                        
                        # Sumar a la etiqueta
                        dict_etq = cuentas_por_concepto[concepto_id][codigo_cuenta]['etiquetas'][etiqueta_limpia]
                        dict_etq['monto'] += monto_efectivo
                        if mes_proy in meses_lista:
                            dict_etq['montos_por_mes'][mes_proy] += monto_efectivo
                        
            print(f"[FlujoCaja] Proyección de facturas draft procesada con etiquetas")
            
        except Exception as e:
            print(f"[FlujoCaja] Error procesando facturas draft: {e}")
            import traceback
            traceback.print_exc()
        
        # 6. Estructurar resultado por actividad
        conceptos_por_actividad = {"OPERACION": [], "INVERSION": [], "FINANCIAMIENTO": []}
        subtotales_por_actividad = {
            "OPERACION": {m: 0.0 for m in meses_lista},
            "INVERSION": {m: 0.0 for m in meses_lista},
            "FINANCIAMIENTO": {m: 0.0 for m in meses_lista}
        }
        
        for concepto in self.catalogo.get("conceptos", []):
            c_id = concepto.get("id")
            c_tipo = concepto.get("tipo")
            c_actividad = concepto.get("actividad")
            
            if c_tipo != "LINEA" or c_actividad not in conceptos_por_actividad:
                continue
            
            montos_mes = montos_por_concepto_mes.get(c_id, {m: 0.0 for m in meses_lista})
            total_concepto = sum(montos_mes.values())
            
            # Obtener cuentas de este concepto para drill-down
            # Obtener cuentas de este concepto para drill-down
            cuentas_concepto = []
            if c_id in cuentas_por_concepto:
                # Ordenar por monto absoluto total
                sorted_cuentas = sorted(
                    cuentas_por_concepto[c_id].items(),
                    key=lambda x: abs(x[1].get('monto', 0)),
                    reverse=True
                )[:15]  # Top 15 accounts
                
                for k, v in sorted_cuentas:
                    # Ordenar etiquetas por monto absoluto (top 20)
                    etiquetas_dict = v.get("etiquetas", {})
                    # Ahora etiquetas_dict es {nombre: {monto, montos_por_mes}}
                    etiquetas_ordenadas = sorted(
                        etiquetas_dict.items(),
                        key=lambda x: abs(x[1].get('monto', 0) if isinstance(x[1], dict) else x[1]),
                        reverse=True
                    )[:20]  # Top 20 etiquetas por cuenta
                    
                    etiquetas_lista = []
                    for nombre, datos in etiquetas_ordenadas:
                        if isinstance(datos, dict):
                            # Nueva estructura con montos_por_mes
                            etiquetas_lista.append({
                                "nombre": nombre[:60],
                                "monto": round(datos.get("monto", 0), 0),
                                "montos_por_mes": {m: round(datos.get("montos_por_mes", {}).get(m, 0), 0) for m in meses_lista}
                            })
                        else:
                            # Retrocompatibilidad: estructura antigua (solo monto)
                            etiquetas_lista.append({
                                "nombre": nombre[:60],
                                "monto": round(datos, 0),
                                "montos_por_mes": {m: 0 for m in meses_lista}
                            })
                    
                    cuentas_concepto.append({
                        "codigo": k,
                        "nombre": v.get("nombre"),
                        "monto": round(v.get("monto", 0), 0),
                        "cantidad": v.get("cantidad"),
                        "montos_por_mes": {m: round(v.get("montos_por_mes", {}).get(m, 0), 0) for m in meses_lista},
                        "etiquetas": etiquetas_lista  # NUEVO: Lista de etiquetas para drill-down nivel 3
                    })
            
            concepto_resultado = {
                "id": c_id,
                "nombre": concepto.get("nombre"),
                "tipo": c_tipo,
                "nivel": concepto.get("nivel", 3),
                "montos_por_mes": {m: round(montos_mes.get(m, 0), 0) for m in meses_lista},
                "total": round(total_concepto, 0),
                "cuentas": cuentas_concepto  # Para drill-down
            }
            
            conceptos_por_actividad[c_actividad].append(concepto_resultado)
            
            # Sumar a subtotales
            for mes in meses_lista:
                subtotales_por_actividad[c_actividad][mes] += montos_mes.get(mes, 0)
        
        # Construir actividades
        for act_key in ["OPERACION", "INVERSION", "FINANCIAMIENTO"]:
            subtotal_mes = subtotales_por_actividad[act_key]
            resultado["actividades"][act_key] = {
                "nombre": self._get_actividad_nombre(act_key),
                "subtotal_por_mes": {m: round(subtotal_mes.get(m, 0), 0) for m in meses_lista},
                "subtotal": round(sum(subtotal_mes.values()), 0),
                "conceptos": conceptos_por_actividad[act_key]
            }
        
        # 7. Calcular efectivo por mes
        efectivo_acumulado = efectivo_inicial_global
        for mes in meses_lista:
            variacion_mes = sum(
                subtotales_por_actividad[act].get(mes, 0) 
                for act in ["OPERACION", "INVERSION", "FINANCIAMIENTO"]
            )
            efectivo_final_mes = efectivo_acumulado + variacion_mes
            
            resultado["efectivo_por_mes"][mes] = {
                "inicial": round(efectivo_acumulado, 0),
                "variacion": round(variacion_mes, 0),
                "final": round(efectivo_final_mes, 0)
            }
            efectivo_acumulado = efectivo_final_mes
        
        resultado["conciliacion"]["efectivo_final"] = round(efectivo_acumulado, 0)
        resultado["conciliacion"]["variacion_neta"] = round(
            sum(resultado["actividades"][a]["subtotal"] for a in ["OPERACION", "INVERSION", "FINANCIAMIENTO"]),
            0
        )
        
        return resultado
    
    def get_flujo_semanal(self, fecha_inicio: str, fecha_fin: str, 
                          company_id: int = None) -> Dict:
        """
        Genera el Estado de Flujo de Efectivo con granularidad SEMANAL.
        
        Similar a get_flujo_mensualizado pero agrupa los datos por semana ISO (YYYY-WXX).
        
        Returns:
            {
                "semanas": ["2026-W01", "2026-W02", ...],
                "actividades": {...},
                "efectivo_por_semana": {...}
            }
        """
        from datetime import datetime, timedelta
        
        resultado = {
            "meta": {"version": "3.2", "mode": "semanal"},
            "periodo": {"inicio": fecha_inicio, "fin": fecha_fin},
            "generado": datetime.now().isoformat(),
            "semanas": [],
            "meses": [],  # Alias para compatibilidad con frontend
            "actividades": {},
            "conciliacion": {},
            "efectivo_por_mes": {}  # Alias para compatibilidad
        }
        
        # 1. Generar lista de semanas en el rango
        fecha_ini_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d')
        fecha_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d')
        
        semanas_lista = []
        semanas_dict = {}  # {semana_iso: (fecha_inicio_semana, fecha_fin_semana)}
        
        current = fecha_ini_dt
        while current <= fecha_fin_dt:
            iso_year, iso_week, _ = current.isocalendar()
            semana_iso = f"{iso_year}-W{iso_week:02d}"
            
            if semana_iso not in semanas_dict:
                # Calcular inicio (lunes) y fin (domingo) de la semana
                # Encontrar el lunes de esta semana
                dias_desde_lunes = current.weekday()
                inicio_semana = current - timedelta(days=dias_desde_lunes)
                fin_semana = inicio_semana + timedelta(days=6)
                
                semanas_dict[semana_iso] = (inicio_semana, fin_semana)
                semanas_lista.append(semana_iso)
            
            current += timedelta(days=1)
        
        resultado["semanas"] = semanas_lista
        resultado["meses"] = semanas_lista  # Alias para frontend
        
        # 2. Obtener cuentas de efectivo
        cuentas_efectivo_ids = self._get_cuentas_efectivo()
        if not cuentas_efectivo_ids:
            resultado["error"] = "No se encontraron cuentas de efectivo configuradas"
            return resultado
        
        # 3. Efectivo inicial
        fecha_anterior = (fecha_ini_dt - timedelta(days=1)).strftime('%Y-%m-%d')
        efectivo_inicial_global = self._get_saldo_efectivo(fecha_anterior, cuentas_efectivo_ids)
        resultado["conciliacion"]["efectivo_inicial"] = round(efectivo_inicial_global, 0)
        
        # 4. Obtener movimientos de efectivo
        domain = [
            ['account_id', 'in', cuentas_efectivo_ids],
            ['parent_state', 'in', ['posted', 'draft']],
            ['date', '>=', fecha_inicio],
            ['date', '<=', fecha_fin]
        ]
        if company_id:
            domain.append(['company_id', '=', company_id])
        
        try:
            movimientos_efectivo = self.odoo.search_read(
                'account.move.line',
                domain,
                ['move_id'],
                limit=50000
            )
        except Exception as e:
            resultado["error"] = f"Error obteniendo movimientos: {e}"
            return resultado
        
        asientos_ids = list(set(
            m['move_id'][0] if isinstance(m.get('move_id'), (list, tuple)) else m.get('move_id')
            for m in movimientos_efectivo if m.get('move_id')
        ))
        
        if not asientos_ids:
            for act_key in ["OPERACION", "INVERSION", "FINANCIAMIENTO"]:
                resultado["actividades"][act_key] = {
                    "nombre": self._get_actividad_nombre(act_key),
                    "subtotal_por_mes": {s: 0 for s in semanas_lista},
                    "subtotal": 0,
                    "conceptos": []
                }
            return resultado
        
        # 5. Procesar contrapartidas por semana
        montos_por_concepto_semana = {}
        for c in self.catalogo.get("conceptos", []):
            if c.get("tipo") == "LINEA":
                montos_por_concepto_semana[c["id"]] = {s: 0.0 for s in semanas_lista}
        montos_por_concepto_semana[CATEGORIA_NEUTRAL] = {s: 0.0 for s in semanas_lista}
        
        cuentas_por_concepto = {}
        chunk_size = 5000
        
        for i in range(0, len(asientos_ids), chunk_size):
            chunk_ids = asientos_ids[i:i + chunk_size]
            
            domain_contrapartidas = [
                ['move_id', 'in', chunk_ids],
                ['account_id', 'not in', cuentas_efectivo_ids]
            ]
            
            try:
                contrapartidas = self.odoo.search_read(
                    'account.move.line',
                    domain_contrapartidas,
                    ['account_id', 'date', 'balance'],
                    limit=50000
                )
            except Exception as e:
                continue
            
            for cp in contrapartidas:
                fecha = cp.get('date')
                if not fecha:
                    continue
                
                try:
                    fecha_dt = datetime.strptime(str(fecha), '%Y-%m-%d')
                    iso_year, iso_week, _ = fecha_dt.isocalendar()
                    semana_iso = f"{iso_year}-W{iso_week:02d}"
                except:
                    continue
                
                if semana_iso not in semanas_lista:
                    continue
                
                acc_data = cp.get('account_id')
                if not acc_data:
                    continue
                
                acc_display = acc_data[1] if len(acc_data) > 1 else "Unknown"
                codigo_cuenta = acc_display.split(' ')[0] if ' ' in acc_display else acc_display
                nombre_cuenta = acc_display.split(' ', 1)[1] if ' ' in acc_display else ""
                
                categoria = self.mapeo_cuentas.get(codigo_cuenta, CATEGORIA_PENDIENTE)
                categoria = migrar_codigo_antiguo(categoria, self._migracion_codigos)
                
                if categoria == CATEGORIA_NEUTRAL:
                    montos_por_concepto_semana[CATEGORIA_NEUTRAL][semana_iso] += cp.get('balance', 0)
                    continue
                
                monto = -1 * cp.get('balance', 0)
                
                if categoria not in montos_por_concepto_semana:
                    montos_por_concepto_semana[categoria] = {s: 0.0 for s in semanas_lista}
                
                montos_por_concepto_semana[categoria][semana_iso] += monto
                
                if categoria not in cuentas_por_concepto:
                    cuentas_por_concepto[categoria] = {}
                if codigo_cuenta not in cuentas_por_concepto[categoria]:
                    cuentas_por_concepto[categoria][codigo_cuenta] = {
                        "codigo": codigo_cuenta,
                        "nombre": nombre_cuenta,
                        "monto": 0,
                        "cantidad": 0
                    }
                cuentas_por_concepto[categoria][codigo_cuenta]["monto"] += monto
                cuentas_por_concepto[categoria][codigo_cuenta]["cantidad"] += 1
        
        # 6. Construir estructura por actividad
        conceptos_por_actividad = {"OPERACION": [], "INVERSION": [], "FINANCIAMIENTO": []}
        subtotales_por_actividad = {
            "OPERACION": {s: 0.0 for s in semanas_lista},
            "INVERSION": {s: 0.0 for s in semanas_lista},
            "FINANCIAMIENTO": {s: 0.0 for s in semanas_lista}
        }
        
        for c in self.catalogo.get("conceptos", []):
            if c.get("tipo") != "LINEA":
                continue
            
            c_id = c["id"]
            c_actividad = c.get("actividad")
            
            if c_actividad not in conceptos_por_actividad:
                continue
            
            montos_semana = montos_por_concepto_semana.get(c_id, {})
            total = sum(montos_semana.values())
            
            cuentas_list = list(cuentas_por_concepto.get(c_id, {}).values())
            
            concepto_data = {
                "id": c_id,
                "codigo": c_id,
                "nombre": c["nombre"],
                "tipo": "LINEA",
                "nivel": c.get("nivel", 3),
                "order": c.get("orden", 999),
                "montos_por_mes": {s: round(montos_semana.get(s, 0), 0) for s in semanas_lista},
                "total": round(total, 0),
                "cuentas": cuentas_list
            }
            
            conceptos_por_actividad[c_actividad].append(concepto_data)
            
            for semana in semanas_lista:
                subtotales_por_actividad[c_actividad][semana] += montos_semana.get(semana, 0)
        
        for act_key in ["OPERACION", "INVERSION", "FINANCIAMIENTO"]:
            subtotal_semana = subtotales_por_actividad[act_key]
            resultado["actividades"][act_key] = {
                "nombre": self._get_actividad_nombre(act_key),
                "subtotal_por_mes": {s: round(subtotal_semana.get(s, 0), 0) for s in semanas_lista},
                "subtotal": round(sum(subtotal_semana.values()), 0),
                "conceptos": conceptos_por_actividad[act_key]
            }
        
        # 7. Efectivo por semana
        efectivo_acumulado = efectivo_inicial_global
        for semana in semanas_lista:
            variacion_semana = sum(
                subtotales_por_actividad[act].get(semana, 0)
                for act in ["OPERACION", "INVERSION", "FINANCIAMIENTO"]
            )
            efectivo_final_semana = efectivo_acumulado + variacion_semana
            
            resultado["efectivo_por_mes"][semana] = {
                "inicial": round(efectivo_acumulado, 0),
                "variacion": round(variacion_semana, 0),
                "final": round(efectivo_final_semana, 0)
            }
            efectivo_acumulado = efectivo_final_semana
        
        resultado["conciliacion"]["efectivo_final"] = round(efectivo_acumulado, 0)
        resultado["conciliacion"]["variacion_neta"] = round(
            sum(resultado["actividades"][a]["subtotal"] for a in ["OPERACION", "INVERSION", "FINANCIAMIENTO"]),
            0
        )
        
        return resultado
    
    def _get_actividad_nombre(self, key: str) -> str:
        """Retorna el nombre completo de una actividad."""
        nombres = {
            "OPERACION": "1. Flujos de efectivo procedentes (utilizados) en actividades de operación",
            "INVERSION": "2. Flujos de efectivo procedentes de (utilizados) en actividades de inversión",
            "FINANCIAMIENTO": "3. Flujos de efectivo procedentes de (utilizados) en actividades de financiamiento"
        }
        return nombres.get(key, key)
    
    def _parse_odoo_month(self, odoo_month: str) -> str:
        """
        Parsea el formato de mes de Odoo ('Enero 2026') a 'YYYY-MM'.
        Odoo puede retornar en español o inglés dependiendo del idioma del usuario.
        """
        meses_es = {
            "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
            "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
            "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12"
        }
        meses_en = {
            "january": "01", "february": "02", "march": "03", "april": "04",
            "may": "05", "june": "06", "july": "07", "august": "08",
            "september": "09", "october": "10", "november": "11", "december": "12"
        }
        
        try:
            parts = odoo_month.strip().lower().split()
            if len(parts) >= 2:
                mes_nombre = parts[0]
                año = parts[1]
                
                mes_num = meses_es.get(mes_nombre) or meses_en.get(mes_nombre)
                if mes_num and año.isdigit():
                    return f"{año}-{mes_num}"
        except:
            pass
        
        return None

    def get_flujo_efectivo(self, fecha_inicio: str, fecha_fin: str, 
                           company_id: int = None) -> Dict:
        """
        Genera el Estado de Flujo de Efectivo para el período indicado.
        
        Método Directo: Analiza movimientos en cuentas de efectivo y clasifica
        según la contrapartida del asiento.
        """
        resultado = {
            "meta": {"version": "3.1", "mode": "hierarchical"},  # Bump version
            "periodo": {"inicio": fecha_inicio, "fin": fecha_fin},
            "generado": datetime.now().isoformat(),
            "actividades": {},
            "proyeccion": {},  # Nuevo campo para flujo proyectado
            "conciliacion": {},
            "detalle_movimientos": []
        }
        
        # 1. Obtener cuentas de efectivo
        cuentas_efectivo_ids = self._get_cuentas_efectivo()
        if not cuentas_efectivo_ids:
            resultado["error"] = "No se encontraron cuentas de efectivo configuradas"
            return resultado
        
        # 2. Calcular efectivo inicial (día anterior al inicio)
        fecha_inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d')
        fecha_anterior = (fecha_inicio_dt - timedelta(days=1)).strftime('%Y-%m-%d')
        efectivo_inicial = self._get_saldo_efectivo(fecha_anterior, cuentas_efectivo_ids)
        
        # 3. Obtener IDs de movimientos de efectivo (para filtrar contrapartidas)
        domain = [
            ['account_id', 'in', cuentas_efectivo_ids],
            ['parent_state', '=', 'posted'],
            ['date', '>=', fecha_inicio],
            ['date', '<=', fecha_fin]
        ]
        if company_id:
            domain.append(['company_id', '=', company_id])
        
        try:
            # OPTIMIZACION: Solo traemos IDs, no objetos completos
            movimientos_efectivo = self.odoo.search_read(
                'account.move.line',
                domain,
                ['move_id', 'date', 'name', 'ref', 'balance', 'account_id', 'partner_id'], # Traemos data para detalle sample
                limit=50000, # Aumentado limit ya que es ligero
                order='date desc' # Descendente para obtener los últimos movimientos para detalle
            )
        except Exception as e:
            resultado["error"] = f"Error obteniendo movimientos: {e}"
            return resultado
            
        # Extraer IDs de asientos (move_id) únicos
        asientos_ids = list(set(
            m['move_id'][0] if isinstance(m.get('move_id'), (list, tuple)) else m.get('move_id')
            for m in movimientos_efectivo if m.get('move_id')
        ))
        
        # 4. AGREGACIÓN SERVER-SIDE: Obtener saldo por cuenta de contrapartida
        # En lugar de traer cada línea, pedimos a Odoo que sume por cuenta
        montos_por_concepto = {}
        # Inicializar
        for c in self.catalogo.get("conceptos", []):
            if c.get("tipo") == "LINEA":
                montos_por_concepto[c["id"]] = 0.0
        montos_por_concepto[CATEGORIA_NEUTRAL] = 0.0
        
        cuentas_pendientes = {}
        cuentas_por_concepto = {} 
        
        def agregar_cuenta_concepto(concepto_id: str, codigo: str, nombre: str, monto: float, es_pendiente: bool = False, cantidad: int = 1):
            """Helper para agregar cuenta a tracking de concepto."""
            if concepto_id not in cuentas_por_concepto:
                cuentas_por_concepto[concepto_id] = {}
            if codigo not in cuentas_por_concepto[concepto_id]:
                cuentas_por_concepto[concepto_id][codigo] = {'nombre': nombre, 'monto': 0, 'cantidad': 0, 'pendiente': es_pendiente}
            cuentas_por_concepto[concepto_id][codigo]['monto'] += monto
            cuentas_por_concepto[concepto_id][codigo]['cantidad'] += cantidad

        # Procesar en chunks de 5000 asientos para no romper URL limit
        chunk_size = 5000
        for i in range(0, len(asientos_ids), chunk_size):
            chunk_asientos = asientos_ids[i:i + chunk_size]
            
            try:
                # read_group: Sumar balance agrupado por account_id
                # Filtro: Pertenecen a los asientos de caja, PERO NO son cuentas de caja
                grupos = self.odoo.models.execute_kw(
                    self.odoo.db, self.odoo.uid, self.odoo.password,
                    'account.move.line', 'read_group',
                    [[
                        ['move_id', 'in', chunk_asientos],
                        ['account_id', 'not in', cuentas_efectivo_ids]
                    ]],
                    {'fields': ['balance', 'account_id'], 'groupby': ['account_id'], 'lazy': False}
                )
                
                # Procesar grupos agregados
                # Obtener lista de cuentas monitoreadas (si existe)
                cuentas_contrapartida_monitoreadas = self.cuentas_monitoreadas.get("cuentas_contrapartida", {}).get("codigos", [])
                filtrar_por_monitoreadas = len(cuentas_contrapartida_monitoreadas) > 0
                
                # DEBUG: Log para verificar que el filtro está activo
                print(f"[FlujoCaja] Filtro activado: {filtrar_por_monitoreadas}, cuentas: {cuentas_contrapartida_monitoreadas[:5]}... (total: {len(cuentas_contrapartida_monitoreadas)})")
                
                for grupo in grupos:
                    # account_id viene como [id, "Code Name"] o [id, "Name"] dependiendo configuración
                    # Necesitamos el ID para buscar code/name limpios si es necesario, 
                    # pero read_group a veces devuelve tuple.
                    acc_data = grupo.get('account_id')
                    balance = grupo.get('balance', 0)
                    count = grupo.get('__count', 1)
                    
                    if not acc_data:
                        continue
                        
                    acc_id = acc_data[0]
                    acc_display = acc_data[1] if len(acc_data) > 1 else "Unknown"
                    
                    # Intentar extraer código del display (usualmente "110101 Caja")
                    # Si no, buscar en un cache o mapa
                    codigo_cuenta = acc_display.split(' ')[0] if ' ' in acc_display else acc_display
                    nombre_cuenta = ' '.join(acc_display.split(' ')[1:]) if ' ' in acc_display else acc_display
                    
                    # FILTRO: Si hay lista de cuentas monitoreadas, SOLO procesar esas
                    if filtrar_por_monitoreadas and codigo_cuenta not in cuentas_contrapartida_monitoreadas:
                        continue  # Ignorar esta cuenta, no está en la lista monitoreada
                    
                    # Clasificar
                    concepto_id, es_pendiente = self._clasificar_cuenta(codigo_cuenta)
                    
                    # NUEVO: Si no tiene mapeo (concepto_id=None), ignorar la cuenta
                    if concepto_id is None:
                        continue  # Cuenta sin mapeo, no procesar
                    
                    # NEUTRAL
                    if concepto_id == CATEGORIA_NEUTRAL:
                        montos_por_concepto[CATEGORIA_NEUTRAL] += balance
                        agregar_cuenta_concepto(CATEGORIA_NEUTRAL, codigo_cuenta, nombre_cuenta, balance, cantidad=count)
                    else:
                        if concepto_id not in montos_por_concepto:
                            montos_por_concepto[concepto_id] = 0.0
                        montos_por_concepto[concepto_id] += balance
                        agregar_cuenta_concepto(concepto_id, codigo_cuenta, nombre_cuenta, balance, es_pendiente, cantidad=count)
                    
                    # Track pendientes
                    if es_pendiente and codigo_cuenta:
                        if codigo_cuenta not in cuentas_pendientes:
                            cuentas_pendientes[codigo_cuenta] = {'nombre': nombre_cuenta, 'monto': 0, 'cantidad': 0}
                        cuentas_pendientes[codigo_cuenta]['monto'] += balance
                        cuentas_pendientes[codigo_cuenta]['cantidad'] += count

            except Exception as e:
                print(f"[FlujoCaja] Error en chunk aggregation: {e}")
        
        # 4b. INYECTAR CUENTAS MONITOREADAS CON SALDO 0 (Si no tuvieron movimientos)
        # El usuario quiere ver las cuentas configuradas explícitamente incluso si son 0.
        try:
            cuentas_monitoreadas_codigos = self.cuentas_monitoreadas.get("cuentas_contrapartida", {}).get("codigos", [])
            mapeo_sugerido = self.cuentas_monitoreadas.get("mapeo_sugerido", {})
            
            # Recopilar cuentas ya procesadas (en movimientos)
            cuentas_procesadas = set()
            for c_counts in cuentas_por_concepto.values():
                cuentas_procesadas.update(c_counts.keys())
            
            # Identificar faltantes
            cuentas_faltantes = [c for c in cuentas_monitoreadas_codigos if c not in cuentas_procesadas]
            
            if cuentas_faltantes:
                # Obtener nombres reales de Odoo para las faltantes (mejor que usar solo código)
                cuentas_info_extra = {}
                try:
                    accs = self.odoo.search_read(
                        'account.account', 
                        [['code', 'in', cuentas_faltantes]], 
                        ['code', 'name']
                    )
                    cuentas_info_extra = {a['code']: a['name'] for a in accs}
                except:
                    pass
                
                for codigo in cuentas_faltantes:
                    # Usar nombre de mapa sugerido o de Odoo o genérico
                    nombre = ""
                    if codigo in mapeo_sugerido:
                        nombre = mapeo_sugerido[codigo].get("nombre", "")
                    
                    if not nombre and codigo in cuentas_info_extra:
                        nombre = cuentas_info_extra[codigo]
                        
                    if not nombre:
                        nombre = f"Cuenta {codigo}"
                        
                    # Clasificar
                    concepto_id, es_pendiente = self._clasificar_cuenta(codigo)
                    
                    if concepto_id == CATEGORIA_NEUTRAL:
                        # Neutrales 0 no suelen interesarnos, pero las agregamos igual si el usuario las pide
                        if CATEGORIA_NEUTRAL not in cuentas_por_concepto:
                            cuentas_por_concepto[CATEGORIA_NEUTRAL] = {}
                        cuentas_por_concepto[CATEGORIA_NEUTRAL][codigo] = {'nombre': nombre, 'monto': 0.0, 'cantidad': 0, 'pendiente': False}
                    else:
                        if concepto_id not in cuentas_por_concepto:
                             cuentas_por_concepto[concepto_id] = {}
                        cuentas_por_concepto[concepto_id][codigo] = {
                            'nombre': nombre, 
                            'monto': 0.0, 
                            'cantidad': 0, 
                            'pendiente': es_pendiente
                        }
                        # No sumamos a montos_por_concepto porque es 0
        except Exception as e:
            print(f"[FlujoCaja] Error inyectando cuentas 0: {e}")
        
        # 5. Generar detalle de últimos movimientos (Muestra)
        # Usamos los movimientos fetching al principio (ya ordenados desc por fecha)
        detalle = []
        for mov in movimientos_efectivo[:100]: # Top 100
             # Nota: Esto es una simplificación. Muestra el movimiento de CAJA, no la contrapartida exacta.
             # Para el usuario es suficiente ver "Pago Factura X - $5000".
             monto = mov.get('balance', 0)
             detalle.append({
                "fecha": mov.get('date'),
                "descripcion": mov.get('name') or mov.get('ref') or '',
                "monto": monto,
                "clasificacion": "Ver desglose", # No calculamos línea por línea para ahorrar
                "contrapartida": mov.get('partner_id')[1] if mov.get('partner_id') else "Varios"
            })
        
        # 6. Estructurar resultado
        # 6. Construir resultado usando el catálogo oficial
        resultado["catalogo"] = self.get_catalogo_conceptos()  # Para UI reference
        
        # Helper para calcular montos de Headers/Totales recursivamente o por hijos
        def calcular_monto_nodo(nodo_id):
            monto_total = 0.0
            # Buscar todos los LINEA que empiezan con este prefijo (jerarquía)
            prefix = nodo_id + "."
            for c_id, monto in montos_por_concepto.items():
                if c_id == nodo_id or c_id.startswith(prefix):
                    if c_id == CATEGORIA_NEUTRAL:
                        continue
                    monto_total += monto
            return monto_total

        # Agrupar conceptos por actividad
        conceptos_por_actividad = {"OPERACION": [], "INVERSION": [], "FINANCIAMIENTO": [], "CONCILIACION": []}
        subtotales = {"OPERACION": 0.0, "INVERSION": 0.0, "FINANCIAMIENTO": 0.0}
        
        for concepto in self.catalogo.get("conceptos", []):
            c_id = concepto.get("id")
            c_tipo = concepto.get("tipo")
            c_actividad = concepto.get("actividad")
            
            # Monto para este nodo
            if c_tipo == "LINEA":
                monto_nodo = montos_por_concepto.get(c_id, 0.0)
            else:
                monto_nodo = calcular_monto_nodo(c_id)
            
            # Obtener cuentas de este concepto desde tracking (solo para LINEA)
            cuentas_concepto = []
            if c_tipo == "LINEA" and c_id in cuentas_por_concepto:
                cuentas_concepto = sorted(
                    [{"codigo": k, **v} for k, v in cuentas_por_concepto[c_id].items()],
                    key=lambda x: abs(x.get('monto', 0)),
                    reverse=True
                )
            
            concepto_resultado = {
                "id": c_id,
                "nombre": concepto.get("nombre"),
                "tipo": c_tipo,
                "nivel": concepto.get("nivel", 3),
                "monto": round(monto_nodo, 0),
                "signo": concepto.get("signo", 1),
                "cuentas": cuentas_concepto,
                "calculo": concepto.get("calculo")
            }
            
            if c_actividad in conceptos_por_actividad:
                conceptos_por_actividad[c_actividad].append(concepto_resultado)
                # Subtotales de actividad se basan en LINEAs (ya que HEADERS duplicarían)
                if c_tipo == "LINEA" and c_actividad in subtotales:
                    subtotales[c_actividad] += monto_nodo
        
        # Construir actividades con la estructura esperada por el frontend
        resultado["actividades"] = {
            "OPERACION": {
                "nombre": "1. Flujos de efectivo procedentes (utilizados) en actividades de operación",
                "subtotal": round(subtotales["OPERACION"], 0),
                "subtotal_nombre": "Flujos de efectivo netos procedentes de (utilizados en) actividades de operación",
                "conceptos": conceptos_por_actividad["OPERACION"]
            },
            "INVERSION": {
                "nombre": "2. Flujos de efectivo procedentes de (utilizados) en actividades de inversión",
                "subtotal": round(subtotales["INVERSION"], 0),
                "subtotal_nombre": "Flujos de efectivo netos procedentes de (utilizados en) actividades de inversión",
                "conceptos": conceptos_por_actividad["INVERSION"]
            },
            "FINANCIAMIENTO": {
                "nombre": "3. Flujos de efectivo procedentes de (utilizados) en actividades de financiamiento",
                "subtotal": round(subtotales["FINANCIAMIENTO"], 0),
                "subtotal_nombre": "Flujos de efectivo netos procedentes de (utilizados en) actividades de financiamiento",
                "conceptos": conceptos_por_actividad["FINANCIAMIENTO"]
            }
        }
        
        # 7. Conciliación
        flujo_operacion = subtotales["OPERACION"]
        flujo_inversion = subtotales["INVERSION"]
        flujo_financiamiento = subtotales["FINANCIAMIENTO"]
        
        # Montos técnicos/especiales
        efecto_tc = montos_por_concepto.get("3.2.3", 0)  # Efectos variación TC
        neutral = montos_por_concepto.get(CATEGORIA_NEUTRAL, 0)  # NO se suma
        
        # Monto de cuentas pendientes de mapeo (ya está en 1.2.6)
        monto_pendientes = sum(c.get('monto', 0) for c in cuentas_pendientes.values())
        
        # Variación neta
        variacion_neta = flujo_operacion + flujo_inversion + flujo_financiamiento
        efectivo_final_calculado = efectivo_inicial + variacion_neta + efecto_tc
        
        resultado["conciliacion"] = {
            "incremento_neto": round(variacion_neta, 0),
            "efecto_tipo_cambio": round(efecto_tc, 0),
            "variacion_efectivo": round(variacion_neta + efecto_tc, 0),
            "efectivo_inicial": round(efectivo_inicial, 0),
            "efectivo_final": round(efectivo_final_calculado, 0),
            "monto_pendientes": round(monto_pendientes, 0),
            "neutral": round(neutral, 0),
            "otros_no_clasificados": round(monto_pendientes, 0)  # Legacy compatibility
        }
        
        # Agregar lista de cuentas pendientes de mapeo para el editor
        resultado["cuentas_pendientes"] = sorted(
            [{"codigo": k, **v} for k, v in cuentas_pendientes.items()],
            key=lambda x: abs(x.get('monto', 0)),
            reverse=True
        )[:50]  # Top 50
        resultado["cuentas_sin_clasificar"] = resultado["cuentas_pendientes"]  # Legacy
        
        # DRILL-DOWN: Cuentas por concepto para inspección
        drill_down = {}
        for concepto_id, cuentas in cuentas_por_concepto.items():
            cuentas_lista = sorted(
                [{"codigo": k, "concepto_id": concepto_id, **v} for k, v in cuentas.items()],
                key=lambda x: abs(x.get('monto', 0)),
                reverse=True
            )[:30]  # Top 30 por concepto
            drill_down[concepto_id] = cuentas_lista
        resultado["drill_down"] = drill_down

        # Agregar historial de cambios para el editor
        mapeo_raw = self._cargar_mapeo()
        resultado["historial_mapeo"] = mapeo_raw.get("historial_cambios", [])[-30:] # Últimos 30
        
        # DRILL-DOWN: Detalle de cuentas de efectivo (para efectivo inicial/final)
        # Necesitamos volver a buscar la info de estas cuentas ya que eliminamos la carga masiva anterior
        cuentas_efectivo_info = []
        if cuentas_efectivo_ids:
            try:
                # Buscar info de cuentas de efectivo
                ce_read = self.odoo.read('account.account', cuentas_efectivo_ids, ['code', 'name'])
                ce_map = {c['id']: c for c in ce_read}
                
                for cid in cuentas_efectivo_ids:
                    if cid in ce_map:
                        c = ce_map[cid]
                        cuentas_efectivo_info.append({
                            "id": cid,
                            "codigo": c.get('code', ''),
                            "nombre": c.get('name', ''),
                            "tipo": "efectivo" if any(c.get('code', '').startswith(p) for p in ["1101", "1102"]) else "equivalente"
                        })
            except Exception as e:
                print(f"[FlujoCaja] Error recuperando info cuentas efectivo: {e}")
        
        resultado["cuentas_efectivo_detalle"] = cuentas_efectivo_info
        
        # 8. Validaciones
        validacion = self.validar_flujo(
            montos_por_concepto, 
            efectivo_inicial, 
            efectivo_final_calculado,
            flujos_por_actividad=resultado["actividades"]
        )
        resultado["validacion"] = validacion
        
        resultado["detalle_movimientos"] = detalle
        resultado["total_movimientos"] = len(movimientos_efectivo)
        
        # 9. Calcular Flujo Proyectado (Facturas borradores/abiertas)
        try:
            resultado["proyeccion"] = self._calcular_flujo_proyectado(fecha_inicio, fecha_fin, company_id)
        except Exception as e:
            print(f"[FlujoCaja] Error calculando proyección: {e}")
            resultado["proyeccion"] = {"error": str(e)}
            
        return resultado

    def _calcular_flujo_proyectado(self, fecha_inicio: str, fecha_fin: str, company_id: int = None) -> Dict:
        """
        Calcula el flujo proyectado basado en documentos (facturas de cliente y proveedor).
        
        Criterios:
        - Estado: Borrador (draft) O Publicado no pagado (posted & != paid)
        - Fecha: invoice_date_due (vencimiento) dentro del rango
        - Clasificación: Basada en las líneas de factura (invoice_line_ids)
        """
        proyeccion = {
            "actividades": {},
            "total_ingresos": 0.0,
            "total_egresos": 0.0
        }
        
        # Inicializar estructura
        detalles_por_concepto = {}  # {codigo_concepto: [documentos]}
        montos_por_concepto = {}    # {codigo_concepto: monto}
        
        for k, v in ESTRUCTURA_FLUJO.items():
            for linea in v["lineas"]:
                detalles_por_concepto[linea["codigo"]] = []
                montos_por_concepto[linea["codigo"]] = 0.0

        # 1. Buscar facturas (Clientes y Proveedores)
        # Lógica mejorada para proyeccion de borradores:
        # - Si tiene fecha vencimiento (invoice_date_due), usarla.
        # - Si es borrador, a veces no tiene vencimiento, usar invoice_date o date.
        
        # Filtro base: Tipos y Estado
        domain_base = [
            ('move_type', 'in', ['out_invoice', 'in_invoice']),
            ('state', '!=', 'cancel'),
            '|', ('state', '=', 'draft'), '&', ('state', '=', 'posted'), ('payment_state', '!=', 'paid')
        ]
        
        if company_id:
            domain_base.append(('company_id', '=', company_id))
            
        # Filtro fecha: Incluir documentos donde CUALQUIERA de estas fechas esté en rango:
        # - x_studio_fecha_de_pago (fecha acordada de pago)
        # - invoice_date_due (vencimiento estándar)
        # - invoice_date (fecha de factura - para borradores sin vencimiento)
        # Odoo domains use Polish Notation (prefix)
        
        domain = domain_base + [
            '|', '|',
                '&', ('x_studio_fecha_de_pago', '>=', fecha_inicio), ('x_studio_fecha_de_pago', '<=', fecha_fin),
                '&', ('invoice_date_due', '>=', fecha_inicio), ('invoice_date_due', '<=', fecha_fin),
                '&', ('invoice_date', '>=', fecha_inicio), ('invoice_date', '<=', fecha_fin)
        ]
            
        campos_move = ['id', 'name', 'ref', 'partner_id', 'invoice_date', 'invoice_date_due', 'amount_total', 
                       'amount_residual', 'move_type', 'state', 'payment_state', 'date', 'x_studio_fecha_de_pago']
        
        try:
            moves = self.odoo.search_read('account.move', domain, campos_move, limit=2000)
            # print(f"[FlujoProyeccion] Found {len(moves)} moves for projection")
        except Exception as e:
            # Fallback if x_studio field fails
            if "x_studio_fecha_de_pago" in str(e):
                print(f"[FlujoProyeccion] Custom field not found, retrying standard: {e}")
                campos_move.remove('x_studio_fecha_de_pago')
                try:
                    moves = self.odoo.search_read('account.move', domain, campos_move, limit=2000)
                except Exception as e2:
                    print(f"[FlujoProyeccion] Error fetching moves retry: {e2}")
                    return proyeccion
            else:
                print(f"[FlujoProyeccion] Error fetching moves: {e}")
                return proyeccion

        if not moves:
            return proyeccion
            
        # 2. Obtener líneas para clasificación (Batch)
        move_ids = [m['id'] for m in moves]
        
        # Filtrar por display_type para obtener las líneas "reales" (productos/servicios)
        # y evitar líneas de impuestos automáticos, secciones o notas.
        domain_lines = [
            ('move_id', 'in', move_ids),
            ('display_type', 'not in', ['line_section', 'line_note'])
        ]
        
        campos_lines = ['move_id', 'account_id', 'price_subtotal', 'name']
        try:
            lines = self.odoo.search_read('account.move.line', domain_lines, campos_lines, limit=10000)
        except Exception as e:
            print(f"[FlujoProyeccion] Error fetching lines: {e}")
            return proyeccion
            
        # Agrupar líneas por move_id
        lines_by_move = {}
        for l in lines:
            mid = l['move_id'][0] if isinstance(l.get('move_id'), (list, tuple)) else l.get('move_id')
            lines_by_move.setdefault(mid, []).append(l)
            
        # Cache de info de cuentas para mapeo
        account_ids = list(set(
            l['account_id'][0] if isinstance(l.get('account_id'), (list, tuple)) else l.get('account_id')
            for l in lines if l.get('account_id')
        ))
        cuentas_info = {}
        if account_ids:
            try:
                acc_read = self.odoo.read('account.account', account_ids, ['code', 'name'])
                cuentas_info = {a['id']: a for a in acc_read}
            except: pass
        
        # Nota: analytic_tag_ids no disponible en esta versión de Odoo
        tags_info = {}
        
        # Contadores para warnings
        docs_sin_etiqueta = []  # Lista de documentos sin etiquetas

        # 3. Procesar cada documento
        from datetime import datetime, timedelta

        for move in moves:
            move_id = move['id']
            # Usar amount_residual (lo que falta por pagar) para proyección, salvo que sea draft (todo)
            monto_documento = move.get('amount_residual', 0) if move.get('state') == 'posted' else move.get('amount_total', 0)
            
            if monto_documento == 0:
                continue
            
            # --- LOGICA DE FECHAS (Prioridad Usuario) ---
            # 1. Fecha Acordada de Pago (x_studio_fecha_de_pago)
            # 2. Vencimiento (invoice_date_due)
            # 3. Estimación Borrador (invoice_date + 30 días)
            
            fecha_pago_acordada = move.get('x_studio_fecha_de_pago')
            fecha_vencimiento = move.get('invoice_date_due')
            fecha_factura = move.get('invoice_date') or move.get('date')
            
            fecha_proyeccion = None
            es_estimada = False
            
            if fecha_pago_acordada:
                fecha_proyeccion = fecha_pago_acordada
            elif fecha_vencimiento:
                fecha_proyeccion = fecha_vencimiento
            elif move.get('state') == 'draft' and fecha_factura:
                # Estimación +30 días
                try:
                    dt_factura = datetime.strptime(fecha_factura, '%Y-%m-%d')
                    dt_estimada = dt_factura + timedelta(days=30)
                    fecha_proyeccion = dt_estimada.strftime('%Y-%m-%d')
                    es_estimada = True
                except:
                    pass
            
            # Si no logramos determinar fecha, usar fecha documento como fallback ultimo
            if not fecha_proyeccion:
                fecha_proyeccion = fecha_factura
                
            # --- FILTRO FINAL POR FECHA PROYECCION ---
            # El query trajo un rango amplio, ahora filtramos exacto por la fecha real de flujo
            if not fecha_proyeccion or not (fecha_inicio <= fecha_proyeccion <= fecha_fin):
                continue
                
            # Determinar signo flujo (Cliente +, Proveedor -)
            es_ingreso = move['move_type'] == 'out_invoice'
            signo_flujo = 1 if es_ingreso else -1
            monto_flujo = monto_documento * signo_flujo
            
            # Obtener líneas base para distribuir
            base_lines = lines_by_move.get(move_id, [])
            total_base = sum(l.get('price_subtotal', 0) for l in base_lines)
            
            # Si no hay líneas base (raro), asignar a UNCLASSIFIED
            if not base_lines or total_base == 0:
                # Fallback: Asignar todo a UNCLASSIFIED
                # O podríamos intentar mapear la cuenta receivable/payable si quisiéramos, pero mejor alertar
                continue

            # Distribuir el monto del flujo según el peso de cada línea base
            partner_name = move['partner_id'][1] if isinstance(move.get('partner_id'), (list, tuple)) else (move.get('partner_id') or "Varios")
            
            for line in base_lines:
                subtotal = line.get('price_subtotal', 0)
                if subtotal == 0: continue
                
                # Peso de esta línea en el total de la factura
                peso = subtotal / total_base
                monto_parte = monto_flujo * peso
                
                # Clasificar
                acc_id = line['account_id'][0] if isinstance(line.get('account_id'), (list, tuple)) else line.get('account_id')
                acc_code = cuentas_info.get(acc_id, {}).get('code', '')
                
                categoria, _ = self._clasificar_cuenta(acc_code)
                if not categoria:
                    categoria = "UNCLASSIFIED"
                
                # Agregar a montos (incluso si es UNCLASSIFIED)
                montos_por_concepto[categoria] = montos_por_concepto.get(categoria, 0) + monto_parte
                
                # Resolver etiquetas de la línea
                # analytic_tag_ids no disponible - usar descripción de línea como etiqueta
                etiquetas_nombres = [line.get('name', '')] if line.get('name') else []
                sin_etiqueta = not line.get('name')
                
                # Detalle documento (ENRIQUECIDO con etiquetas)
                entry = {
                    "id": move_id,
                    "documento": move.get('name') or move.get('ref') or str(move_id),
                    "partner": partner_name,
                    "fecha_emision": move.get('invoice_date'),  # Fecha emisión
                    "fecha_venc": fecha_proyeccion, # Usamos la fecha real de flujo
                    "es_estimada": es_estimada,
                    "estado": "Borrador" if move.get('state') == 'draft' else "Abierto",
                    "monto": round(monto_parte, 0),
                    "cuenta": acc_code,
                    "cuenta_nombre": cuentas_info.get(acc_id, {}).get('name', ''),
                    "tipo": "Factura Cliente" if es_ingreso else "Factura Proveedor",
                    "linea_nombre": line.get('name', ''),  # Descripción de la línea (etiqueta usuario)
                    "etiquetas": etiquetas_nombres,  # OBLIGATORIO - Lista de etiquetas
                    "sin_etiqueta": sin_etiqueta  # Warning flag
                }
                
                # Rastrear documentos sin etiquetas para warning
                if sin_etiqueta:
                    if move_id not in [d['id'] for d in docs_sin_etiqueta]:
                        docs_sin_etiqueta.append({
                            "id": move_id,
                            "documento": entry["documento"],
                            "partner": partner_name,
                            "monto": round(monto_flujo, 0)
                        })
                
                if categoria not in detalles_por_concepto:
                    detalles_por_concepto[categoria] = []
                    
                detalles_por_concepto[categoria].append(entry)

        # 4. Construir Resultado Final Estructurado
        proyeccion["sin_clasificar"] = []
        if "UNCLASSIFIED" in detalles_por_concepto:
             proyeccion["sin_clasificar"] = detalles_por_concepto["UNCLASSIFIED"]
             proyeccion["monto_sin_clasificar"] = montos_por_concepto.get("UNCLASSIFIED", 0)

        for cat_key, cat_data in ESTRUCTURA_FLUJO.items():
            conceptos_res = []
            subtotal_actividad = 0.0
            
            for linea in cat_data["lineas"]:
                codigo = linea["codigo"]
                monto = montos_por_concepto.get(codigo, 0)
                docs = detalles_por_concepto.get(codigo, [])
                
                # Ordenar documentos por fecha calculada
                docs.sort(key=lambda x: x['fecha_venc'] or '9999-12-31')
                
                if monto != 0 or docs:
                    conceptos_res.append({
                        "codigo": codigo,
                        "nombre": linea["nombre"],
                        "monto": round(monto, 0),
                        "documentos": docs
                    })
                    subtotal_actividad += monto
            
            proyeccion["actividades"][cat_key] = {
                "nombre": cat_data["nombre"],
                "subtotal": round(subtotal_actividad, 0),
                "subtotal_nombre": cat_data.get("subtotal_nombre", "Subtotal"),
                "conceptos": conceptos_res
            }
        
        # WARNING: Documentos sin etiquetas (visible en frontend)
        if docs_sin_etiqueta:
            proyeccion["warnings"] = proyeccion.get("warnings", [])
            proyeccion["warnings"].append({
                "tipo": "SIN_ETIQUETAS",
                "mensaje": f"{len(docs_sin_etiqueta)} documento(s) no tienen etiquetas definidas",
                "documentos": docs_sin_etiqueta[:20]  # Limitar a 20 para frontend
            })
            
        return proyeccion
    
    def get_mapeo(self) -> Dict:
        """Retorna el mapeo actual de cuentas."""
        return self.mapeo_cuentas
    
    def get_cuentas_efectivo_detalle(self) -> List[Dict]:
        """Retorna las cuentas de efectivo con su detalle."""
        cuentas_ids = self._get_cuentas_efectivo()
        if not cuentas_ids:
            return []
        
        try:
            cuentas = self.odoo.read('account.account', cuentas_ids, ['id', 'code', 'name'])
            return cuentas
        except:
            return []
    
    def get_diagnostico_no_clasificados(self, fecha_inicio: str, fecha_fin: str,
                                         company_id: int = None) -> Dict:
        """
        Obtiene diagnóstico detallado de cuentas que generan movimientos no clasificados.
        
        Retorna lista de cuentas con sus códigos, nombres y montos para facilitar
        la actualización del mapeo.
        """
        resultado = {
            "periodo": {"inicio": fecha_inicio, "fin": fecha_fin},
            "total_no_clasificado": 0,
            "cuentas_no_clasificadas": [],
            "sugerencias_mapeo": {}
        }
        
        # Obtener cuentas de efectivo
        cuentas_efectivo_ids = self._get_cuentas_efectivo()
        if not cuentas_efectivo_ids:
            resultado["error"] = "No se encontraron cuentas de efectivo"
            return resultado
        
        # Obtener movimientos del período
        domain = [
            ['account_id', 'in', cuentas_efectivo_ids],
            ['parent_state', '=', 'posted'],
            ['date', '>=', fecha_inicio],
            ['date', '<=', fecha_fin]
        ]
        if company_id:
            domain.append(['company_id', '=', company_id])
        
        try:
            movimientos = self.odoo.search_read(
                'account.move.line',
                domain,
                ['id', 'move_id', 'balance'],
                limit=50000
            )
        except Exception as e:
            resultado["error"] = f"Error obteniendo movimientos: {e}"
            return resultado
        
        # Obtener asientos
        asientos_ids = list(set(
            m['move_id'][0] if isinstance(m.get('move_id'), (list, tuple)) else m.get('move_id')
            for m in movimientos if m.get('move_id')
        ))
        
        # Obtener todas las líneas de contrapartida
        contrapartidas_por_asiento = {}
        if asientos_ids:
            try:
                todas_lineas = self.odoo.search_read(
                    'account.move.line',
                    [['move_id', 'in', asientos_ids]],
                    ['id', 'move_id', 'account_id', 'balance'],
                    limit=100000
                )
                for linea in todas_lineas:
                    move_id = linea['move_id'][0] if isinstance(linea.get('move_id'), (list, tuple)) else linea.get('move_id')
                    if move_id not in contrapartidas_por_asiento:
                        contrapartidas_por_asiento[move_id] = []
                    contrapartidas_por_asiento[move_id].append(linea)
            except:
                pass
        
        # Obtener info de cuentas
        cuenta_ids_all = list(set(
            l['account_id'][0] if isinstance(l.get('account_id'), (list, tuple)) else l.get('account_id')
            for lineas in contrapartidas_por_asiento.values() for l in lineas if l.get('account_id')
        ))
        
        cuentas_info = {}
        if cuenta_ids_all:
            try:
                cuentas = self.odoo.read('account.account', cuenta_ids_all, ['id', 'code', 'name'])
                cuentas_info = {c['id']: c for c in cuentas}
            except:
                pass
        
        # Analizar movimientos no clasificados
        no_clasificados = {}  # {codigo: {nombre, monto_total, cantidad}}
        
        for mov in movimientos:
            move_id = mov['move_id'][0] if isinstance(mov.get('move_id'), (list, tuple)) else mov.get('move_id')
            monto = mov.get('balance', 0)
            
            lineas_asiento = contrapartidas_por_asiento.get(move_id, [])
            
            for linea in lineas_asiento:
                linea_account_id = linea['account_id'][0] if isinstance(linea.get('account_id'), (list, tuple)) else linea.get('account_id')
                
                # Solo contrapartidas (no cuentas de efectivo)
                if linea_account_id in cuentas_efectivo_ids:
                    continue
                
                cuenta = cuentas_info.get(linea_account_id, {})
                codigo = cuenta.get('code', 'SIN_CODIGO')
                nombre = cuenta.get('name', 'Sin nombre')
                
                # Verificar si está clasificada
                clasificacion = self._clasificar_cuenta(codigo)
                
                if not clasificacion:
                    # Es no clasificada
                    if codigo not in no_clasificados:
                        no_clasificados[codigo] = {
                            'codigo': codigo,
                            'nombre': nombre,
                            'monto_total': 0,
                            'cantidad_movimientos': 0
                        }
                    no_clasificados[codigo]['monto_total'] += monto
                    no_clasificados[codigo]['cantidad_movimientos'] += 1
        
        # Ordenar por monto (valor absoluto)
        lista_ordenada = sorted(
            no_clasificados.values(),
            key=lambda x: abs(x['monto_total']),
            reverse=True
        )
        
        resultado["cuentas_no_clasificadas"] = lista_ordenada
        resultado["total_no_clasificado"] = sum(c['monto_total'] for c in lista_ordenada)
        resultado["cantidad_cuentas"] = len(lista_ordenada)
        
        # Generar sugerencias de mapeo basadas en prefijos
        sugerencias = {}
        for cuenta in lista_ordenada[:20]:  # Top 20
            codigo = cuenta['codigo']
            prefijo = codigo[:3] if len(codigo) >= 3 else codigo
            
            # Sugerir categoría basada en prefijo típico chileno
            if prefijo.startswith('1'):
                if prefijo in ['110', '111']:
                    categoria = "Efectivo (ya debería estar)"
                elif prefijo.startswith('12'):
                    categoria = "IN03 - PPE o activo fijo"
                elif prefijo.startswith('13') or prefijo.startswith('14'):
                    categoria = "IN01/IN02 - Inversiones"
                else:
                    categoria = "Verificar - Activo"
            elif prefijo.startswith('2'):
                if prefijo in ['210', '211', '212']:
                    categoria = "OP02 - Proveedores"
                elif prefijo in ['215', '216', '217']:
                    categoria = "OP03 - Remuneraciones o OP06 - Impuestos"
                elif prefijo.startswith('22') or prefijo.startswith('23'):
                    categoria = "FI01/FI02 - Préstamos"
                else:
                    categoria = "Verificar - Pasivo"
            elif prefijo.startswith('3'):
                categoria = "FI07 - Patrimonio/Dividendos"
            elif prefijo.startswith('4'):
                categoria = "OP01 - Ingresos" if prefijo in ['410', '411', '412'] else "OP05 - Otros ingresos"
            elif prefijo.startswith('5'):
                categoria = "OP02 - Costos/Gastos operacionales"
            elif prefijo.startswith('6'):
                if prefijo in ['620', '621', '622', '623']:
                    categoria = "OP03 - Remuneraciones"
                elif prefijo in ['650', '651']:
                    categoria = "OP04 - Intereses pagados"
                elif prefijo in ['640', '641']:
                    categoria = "OP06 - Impuestos"
                else:
                    categoria = "OP07 - Otros gastos operacionales"
            else:
                categoria = "Verificar - Categoría desconocida"
            
            sugerencias[codigo] = {
                'nombre': cuenta['nombre'],
                'monto': cuenta['monto_total'],
                'sugerencia': categoria,
                'prefijo': prefijo
            }
        
        resultado["sugerencias_mapeo"] = sugerencias
        
        return resultado

