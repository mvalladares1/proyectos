"""
Servicio de Flujo de Caja - Estado de Flujo de Efectivo NIIF IAS 7 (Método Directo)

Este servicio genera el Estado de Flujo de Efectivo obteniendo datos desde Odoo.
El flujo se construye exclusivamente desde movimientos que afectan cuentas de efectivo.
Usa el catálogo oficial de conceptos NIIF para clasificación.
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import os

from shared.odoo_client import OdooClient


# Concepto fallback para cuentas sin mapear
CONCEPTO_FALLBACK = "1.2.6"  # Otras entradas (salidas) de efectivo

# Estructura IAS 7 para Actividades - FUENTE DE VERDAD
# Solo Operación por ahora (FASE 1)
ESTRUCTURA_FLUJO = {
    "OPERACION": {
        "nombre": "1. Flujos de efectivo procedentes (utilizados) en actividades de operación",
        "lineas": [
            {"codigo": "1.1.1", "nombre": "Cobros procedentes de las ventas de bienes y prestación de servicios", "signo": 1},
            {"codigo": "1.2.1", "nombre": "Pagos a proveedores por el suministro de bienes y servicios", "signo": -1},
            {"codigo": "1.2.2", "nombre": "Pagos a y por cuenta de los empleados", "signo": -1},
            {"codigo": "1.2.3", "nombre": "Intereses pagados", "signo": -1},
            {"codigo": "1.2.4", "nombre": "Intereses recibidos", "signo": 1},
            {"codigo": "1.2.5", "nombre": "Impuestos a las ganancias reembolsados (pagados)", "signo": -1},
            {"codigo": "1.2.6", "nombre": "Otras entradas (salidas) de efectivo", "signo": 1}
        ],
        "subtotal_nombre": "Flujos de efectivo netos procedentes de (utilizados en) actividades de operación"
    },
    "INVERSION": {
        "nombre": "2. Flujos de efectivo procedentes de (utilizados) en actividades de inversión",
        "lineas": [],
        "subtotal_nombre": "Flujos de efectivo netos procedentes de (utilizados) en actividades de inversión"
    },
    "FINANCIAMIENTO": {
        "nombre": "3. Flujos de efectivo procedentes de (utilizados) en actividades de financiamiento",
        "lineas": [],
        "subtotal_nombre": "Flujos de efectivo netos procedentes de (utilizados) en actividades de financiamiento"
    }
}

# Mapeo OBLIGATORIO de cuentas de financiamiento (Parametrización Fija)
CUENTAS_FIJAS_FINANCIAMIENTO = {
    # 3.0.2 Importes procedentes de préstamos de corto plazo
    "21010101": "3.0.2", "21010102": "3.0.2", "21010103": "3.0.2", "82010101": "3.0.2",
    # 3.0.1 Importes procedentes de préstamos de largo plazo
    "21010213": "3.0.1", "21010223": "3.0.1", "22010101": "3.0.1",
    # 3.1.1 Préstamos de entidades relacionadas
    "21030201": "3.1.1", "21030211": "3.1.1", "22020101": "3.1.1",
    # 3.1.4 Pagos de pasivos por arrendamientos financieros
    "21010201": "3.1.4", "21010202": "3.1.4", "21010204": "3.1.4",
    "22010202": "3.1.4", "22010204": "3.1.4", "82010102": "3.1.4"
}


class FlujoCajaService:
    """Servicio para generar Estado de Flujo de Efectivo NIIF IAS 7."""
    
    # Categorías técnicas especiales (no se muestran en UI pero se procesan internamente)
    CATEGORIA_NEUTRAL = "NEUTRAL"       # No impacta flujo (transferencias internas)
    CATEGORIA_PENDIENTE = "PENDIENTE"   # Sin clasificar (va a 1.2.6 + lista pendientes)
    CATEGORIA_UNCLASSIFIED = "1.2.6"    # Otras entradas (salidas) de efectivo - fallback
    CATEGORIA_FX_EFFECT = "4.2"         # Efectos variación tipo de cambio
    
    def __init__(self, username: str = None, password: str = None):
        self.odoo = OdooClient(username=username, password=password)
        self.catalogo = self._cargar_catalogo()
        self.mapeo_cuentas = self._cargar_mapeo()
        self.cuentas_monitoreadas = self._cargar_cuentas_monitoreadas()
        self._cache_cuentas_efectivo = None
        self._migracion_codigos = self.catalogo.get("migracion_codigos", {})
    
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
        Motor de agregación IAS 7.
        
        Toma montos de LINEAs y calcula HEADERs/TOTALs automáticamente.
        
        Args:
            montos_por_linea: {concepto_id: monto_real} ej: {"1.1.1": 1000000, "1.2.1": -500000}
            proyeccion_por_linea: {concepto_id: monto_proyectado} (opcional)
            modo: "real" | "proyectado" | "consolidado"
        
        Returns:
            Lista de nodos con: id, nombre, tipo, nivel, monto_real, monto_proyectado, monto_display
        """
        proyeccion_por_linea = proyeccion_por_linea or {}
        conceptos = self.catalogo.get("conceptos", [])
        sorted_conceptos = sorted(conceptos, key=lambda x: x.get("order", 999))
        
        resultado = []
        
        for concepto in sorted_conceptos:
            c_id = concepto.get("id")
            c_tipo = concepto.get("tipo")
            
            if c_tipo == "LINEA":
                # Montos directos
                monto_real = montos_por_linea.get(c_id, 0.0)
                monto_proy = proyeccion_por_linea.get(c_id, 0.0)
            elif c_tipo in ("HEADER", "TOTAL"):
                # Sumar hijos (nodos cuyo parent == este ID o que empiezan con este prefijo)
                monto_real = self._sumar_hijos(c_id, montos_por_linea, conceptos)
                monto_proy = self._sumar_hijos(c_id, proyeccion_por_linea, conceptos)
            else:
                # DATA u otros
                monto_real = montos_por_linea.get(c_id, 0.0)
                monto_proy = proyeccion_por_linea.get(c_id, 0.0)
            
            # Determinar monto a mostrar según modo
            if modo == "real":
                monto_display = monto_real
            elif modo == "proyectado":
                monto_display = monto_proy
            else:  # consolidado
                monto_display = monto_real + monto_proy
            
            resultado.append({
                "id": c_id,
                "nombre": concepto.get("nombre"),
                "tipo": c_tipo,
                "nivel": concepto.get("nivel", 3),
                "parent": concepto.get("parent"),
                "order": concepto.get("order"),
                "signo": concepto.get("signo", 1),
                "actividad": concepto.get("actividad"),
                "monto_real": round(monto_real, 0),
                "monto_proyectado": round(monto_proy, 0),
                "monto_display": round(monto_display, 0)
            })
        
        return resultado
    
    def _sumar_hijos(self, parent_id: str, montos: Dict[str, float], conceptos: List[Dict]) -> float:
        """
        Suma los montos de todos los hijos directos e indirectos de un nodo.
        Solo suma LINEAs para evitar doble conteo.
        """
        total = 0.0
        prefix = parent_id + "."
        
        for concepto in conceptos:
            c_id = concepto.get("id", "")
            c_tipo = concepto.get("tipo", "")
            
            # Solo sumar LINEAs que son hijos (directos o indirectos)
            if c_tipo == "LINEA":
                if c_id.startswith(prefix) or concepto.get("parent") == parent_id:
                    total += montos.get(c_id, 0.0)
        
        return total
    
    def get_categorias_ias7_dropdown(self) -> List[Dict]:
        """
        Retorna las categorías para el dropdown del editor.
        Formato: {"label": "1.1.1 - Cobros procedentes...", "value": "1.1.1"}
        Solo incluye LINEAs (donde se pueden mapear cuentas).
        """
        conceptos = self.catalogo.get("conceptos", [])
        lineas = [c for c in conceptos if c.get("tipo") == "LINEA"]
        sorted_lineas = sorted(lineas, key=lambda x: x.get("order", 999))
        
        resultado = []
        for c in sorted_lineas:
            actividad = c.get("actividad", "")
            # Emoji por actividad
            emoji = {"OPERACION": "🟢", "INVERSION": "🔵", "FINANCIAMIENTO": "🟣", "CONCILIACION": "⚪"}.get(actividad, "⚪")
            
            resultado.append({
                "label": f"{emoji} {c['id']} - {c['nombre'][:60]}",
                "value": c['id']
            })
        
        # Agregar NEUTRAL al final
        resultado.append({"label": "⚪ NEUTRAL - Transferencias internas (no impacta flujo)", "value": "NEUTRAL"})
        
        return resultado
    
    def _migrar_codigo_antiguo(self, codigo_antiguo: str) -> str:
        """Convierte códigos antiguos (OP01, IN01) a nuevos (1.1.1, 2.1)."""
        return self._migracion_codigos.get(codigo_antiguo, codigo_antiguo)
    
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
        
        # No mapeada → fallback + marcar como pendiente
        return (CONCEPTO_FALLBACK, True)
    
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
        
        neutral = flujos_por_linea.get(self.CATEGORIA_NEUTRAL, 0)
        sin_clasificar = flujos_por_linea.get(self.CATEGORIA_UNCLASSIFIED, 0)
        
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
            total_flujos = sum(abs(v) for k, v in flujos_por_linea.items() if k != self.CATEGORIA_NEUTRAL)
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
                if monto == 0 or codigo in [self.CATEGORIA_NEUTRAL, self.CATEGORIA_UNCLASSIFIED, self.CATEGORIA_FX_EFFECT]:
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
        montos_por_concepto[self.CATEGORIA_NEUTRAL] = 0.0
        
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
                    # NOTA: Para mayor precisión, podríamos cachear todos los accounts IDs -> Codes antes
                    # Pero extraer del display name es usualmente seguro en Odoo estándar.
                    # Si falla, el fallback es UNCLASSIFIED
                    
                    concepto_id, es_pendiente = self._clasificar_cuenta(codigo_cuenta)
                    
                    # NEUTRAL
                    if concepto_id == self.CATEGORIA_NEUTRAL:
                        montos_por_concepto[self.CATEGORIA_NEUTRAL] += balance
                        agregar_cuenta_concepto(self.CATEGORIA_NEUTRAL, codigo_cuenta, nombre_cuenta, balance, cantidad=count)
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
                    if c_id == self.CATEGORIA_NEUTRAL:
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
        neutral = montos_por_concepto.get(self.CATEGORIA_NEUTRAL, 0)  # NO se suma
        
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
            
        # Filtro fecha: O vencimiento en rango O (si no hay vencimiento) fecha en rango
        # Odoo domains use Polish Notation (prefix)
        # OR( AND(inv_due >= start, inv_due <= end), AND(inv_due=False, inv_date >= start, inv_date <= end) )
        
        domain = domain_base + [
            '|',
                '&', ('invoice_date_due', '>=', fecha_inicio), ('invoice_date_due', '<=', fecha_fin),
                '&', '&', ('invoice_date_due', '=', False), ('invoice_date', '>=', fecha_inicio), ('invoice_date', '<=', fecha_fin)
        ]
            
        campos_move = ['id', 'name', 'ref', 'partner_id', 'invoice_date', 'invoice_date_due', 'amount_total', 
                       'amount_residual', 'move_type', 'state', 'payment_state', 'date']
        
        try:
            moves = self.odoo.search_read('account.move', domain, campos_move, limit=2000)
        except Exception as e:
            print(f"[FlujoProyeccion] Error fetching moves: {e}")
            return proyeccion

        if not moves:
            return proyeccion
            
        # 2. Obtener líneas para clasificación (Batch)
        move_ids = [m['id'] for m in moves]
        
        # Usamos exclude_from_invoice_tab=False para obtener las líneas "reales" (productos/servicios)
        # y evitar líneas de impuestos automáticos o cuentas por cobrar/pagar.
        domain_lines = [
            ('move_id', 'in', move_ids),
            ('exclude_from_invoice_tab', '=', False)
        ]
        
        campos_lines = ['move_id', 'account_id', 'price_subtotal', 'analytic_tag_ids', 'name']
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
        
        # Cache de etiquetas analíticas (OBLIGATORIO para proyección)
        tag_ids = list(set(
            tag_id
            for l in lines
            for tag_id in (l.get('analytic_tag_ids') or [])
        ))
        tags_info = {}
        if tag_ids:
            try:
                tags_read = self.odoo.read('account.analytic.tag', tag_ids, ['id', 'name'])
                tags_info = {t['id']: t.get('name', '') for t in tags_read}
            except Exception as e:
                print(f"[FlujoProyeccion] Error fetching tags: {e}")
        
        # Contadores para warnings
        docs_sin_etiqueta = []  # Lista de documentos sin etiquetas

        # 3. Procesar cada documento
        for move in moves:
            move_id = move['id']
            # Usar amount_residual (lo que falta por pagar) para proyección, salvo que sea draft (todo)
            monto_documento = move.get('amount_residual', 0) if move.get('state') == 'posted' else move.get('amount_total', 0)
            
            if monto_documento == 0:
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
                
                categoria = self._clasificar_cuenta(acc_code)
                if not categoria:
                    categoria = "UNCLASSIFIED"
                
                # Agregar a montos (incluso si es UNCLASSIFIED)
                montos_por_concepto[categoria] = montos_por_concepto.get(categoria, 0) + monto_parte
                
                # Resolver etiquetas de la línea
                line_tag_ids = line.get('analytic_tag_ids') or []
                etiquetas_nombres = [tags_info.get(tid, f"Tag_{tid}") for tid in line_tag_ids]
                sin_etiqueta = len(line_tag_ids) == 0
                
                # Detalle documento (ENRIQUECIDO con etiquetas)
                entry = {
                    "id": move_id,
                    "documento": move.get('name') or move.get('ref') or str(move_id),
                    "partner": partner_name,
                    "fecha_emision": move.get('invoice_date'),  # Fecha emisión
                    "fecha_venc": move.get('invoice_date_due'),
                    "estado": "Borrador" if move.get('state') == 'draft' else "Abierto",
                    "monto": round(monto_parte, 0),
                    "cuenta": acc_code,
                    "cuenta_nombre": cuentas_info.get(acc_id, {}).get('name', ''),
                    "tipo": "Factura Cliente" if es_ingreso else "Factura Proveedor",
                    "linea_nombre": line.get('name', ''),  # Descripción de la línea
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
                
                # Ordenar documentos por fecha vencimiento (o emision como fallback)
                docs.sort(key=lambda x: x['fecha_venc'] or x['fecha_emision'] or '9999-12-31')
                
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

