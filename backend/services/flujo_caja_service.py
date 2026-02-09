"""
Servicio de Flujo de Caja - Estado de Flujo de Efectivo NIIF IAS 7 (Método Directo)

Este servicio genera el Estado de Flujo de Efectivo obteniendo datos desde Odoo.
El flujo se construye exclusivamente desde movimientos que afectan cuentas de efectivo.
Usa el catálogo oficial de conceptos NIIF para clasificación.

MODULARIZADO: La lógica está distribuida en módulos especializados:
- odoo_queries.py: Todas las consultas a Odoo
- clasificador.py: Clasificación de cuentas
- agregador.py: Agregación por concepto/período
- proyeccion.py: Cálculo de proyecciones
- validador.py: Validación de flujos
- helpers.py: Funciones auxiliares
- constants.py: Constantes y estructuras
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
from .flujo_caja.odoo_queries import OdooQueryManager
from .flujo_caja.agregador import AgregadorFlujo
from .flujo_caja.proyeccion import ProyeccionFlujo
from .flujo_caja.real_proyectado import RealProyectadoCalculator


class FlujoCajaService:
    """Servicio para generar Estado de Flujo de Efectivo NIIF IAS 7."""
    
    def __init__(self, username: str = None, password: str = None):
        self.username = username
        self.password = password
        self._odoo = None
        self._odoo_manager = None
        self._real_proyectado_calc = None
        self.catalogo = self._cargar_catalogo()
        self.mapeo_cuentas = self._cargar_mapeo()
        self.cuentas_monitoreadas = self._cargar_cuentas_monitoreadas()
        self._migracion_codigos = self.catalogo.get("migracion_codigos", {})
    
    # ==================== PROPIEDADES ====================
    
    @property
    def odoo(self):
        """Lazy initialization de OdooClient."""
        if self._odoo is None:
            self._odoo = OdooClient(username=self.username, password=self.password)
        return self._odoo
    
    @property
    def odoo_manager(self) -> OdooQueryManager:
        """Lazy initialization de OdooQueryManager."""
        if self._odoo_manager is None:
            self._odoo_manager = OdooQueryManager(self.odoo)
        return self._odoo_manager
    
    @property
    def real_proyectado_calc(self) -> RealProyectadoCalculator:
        """Lazy initialization de RealProyectadoCalculator."""
        if self._real_proyectado_calc is None:
            self._real_proyectado_calc = RealProyectadoCalculator(self.odoo)
        return self._real_proyectado_calc
    
    # ==================== CARGA DE CONFIGURACIÓN ====================
    
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
        """Carga la configuración de cuentas monitoreadas."""
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
        """Retorna mapeo por defecto."""
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
    
    # ==================== CATÁLOGO ====================
    
    def get_catalogo_conceptos(self) -> List[Dict]:
        """Retorna la lista de conceptos del catálogo oficial."""
        return self.catalogo.get("conceptos", [])
    
    def get_concepto_por_id(self, concepto_id: str) -> Optional[Dict]:
        """Busca un concepto por su ID."""
        for c in self.catalogo.get("conceptos", []):
            if c.get("id") == concepto_id:
                return c
        return None
    
    def build_ias7_catalog_by_activity(self, actividad: str = None) -> List[Dict]:
        """Retorna conceptos filtrados por actividad ordenados por 'order'."""
        conceptos = self.catalogo.get("conceptos", [])
        if actividad:
            filtered = [c for c in conceptos if c.get("actividad") == actividad.upper()]
        else:
            filtered = conceptos
        return sorted(filtered, key=lambda x: x.get("order", 999))
    
    def aggregate_by_ias7(self, montos_por_linea: Dict[str, float], 
                          proyeccion_por_linea: Dict[str, float] = None,
                          modo: str = "consolidado") -> List[Dict]:
        """Motor de agregación IAS 7 (delegado a helpers)."""
        conceptos = self.catalogo.get("conceptos", [])
        return aggregate_montos_by_concepto(conceptos, montos_por_linea, proyeccion_por_linea, modo)
    
    def get_categorias_ias7_dropdown(self) -> List[Dict]:
        """Retorna categorías para dropdown de clasificación."""
        conceptos = self.catalogo.get("conceptos", [])
        return build_categorias_dropdown(conceptos, EMOJIS_ACTIVIDAD)
    
    # ==================== CLASIFICACIÓN ====================
    
    def _clasificar_cuenta(self, codigo_cuenta: str) -> Tuple[str, bool]:
        """
        Clasifica una cuenta usando mapeo explícito.
        Retorna (concepto_id, es_pendiente).
        """
        # 1. Chequear mapeo OBLIGATORIO (Financiamiento)
        if codigo_cuenta in CUENTAS_FIJAS_FINANCIAMIENTO:
            return (CUENTAS_FIJAS_FINANCIAMIENTO[codigo_cuenta], False)

        mapeo = self.mapeo_cuentas.get("mapeo_cuentas", {})
        
        if codigo_cuenta in mapeo:
            cuenta_info = mapeo[codigo_cuenta]
            if isinstance(cuenta_info, dict):
                concepto_id = cuenta_info.get("concepto_id")
                if concepto_id:
                    return (concepto_id, False)
                categoria = cuenta_info.get("categoria")
                if categoria:
                    nuevo_id = migrar_codigo_antiguo(categoria, self._migracion_codigos)
                    return (nuevo_id, False)
            elif isinstance(cuenta_info, str):
                nuevo_id = migrar_codigo_antiguo(cuenta_info, self._migracion_codigos)
                return (nuevo_id, False)
        
        return (None, True)
    
    # ==================== MAPEO ====================
    
    def guardar_mapeo_cuenta(self, codigo: str, concepto_id: str, nombre: str = "", 
                                usuario: str = "system", impacto_estimado: float = None) -> bool:
        """Guarda o actualiza el mapeo de una cuenta individual."""
        mapeo_path = self._get_mapeo_path()
        try:
            mapeo = self._cargar_mapeo()
            
            concepto_anterior = None
            if "mapeo_cuentas" in mapeo and codigo in mapeo["mapeo_cuentas"]:
                cuenta_ant = mapeo["mapeo_cuentas"][codigo]
                if isinstance(cuenta_ant, dict):
                    concepto_anterior = cuenta_ant.get("concepto_id") or cuenta_ant.get("categoria")
                elif isinstance(cuenta_ant, str):
                    concepto_anterior = cuenta_ant
            
            if "mapeo_cuentas" not in mapeo:
                mapeo["mapeo_cuentas"] = {}
            
            mapeo["mapeo_cuentas"][codigo] = {
                "concepto_id": concepto_id,
                "nombre": nombre,
                "fecha_asignacion": datetime.now().isoformat(),
                "usuario": usuario
            }
            
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
            
            if len(mapeo["historial_cambios"]) > 500:
                mapeo["historial_cambios"] = mapeo["historial_cambios"][-500:]
            
            with open(mapeo_path, 'w', encoding='utf-8') as f:
                json.dump(mapeo, f, indent=2, ensure_ascii=False)
            
            self.mapeo_cuentas = mapeo
            self.odoo_manager.invalidar_cache()
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
    
    def get_mapeo(self) -> Dict:
        """Retorna el mapeo actual de cuentas."""
        return self.mapeo_cuentas
    
    def get_configuracion(self) -> Dict:
        """Retorna la configuración del mapeo."""
        return self.mapeo_cuentas.get("configuracion", {
            "modo_estricto": False,
            "bloquear_si_no_clasificado": False,
            "umbral_alerta_no_clasificado": 0.05
        })
    
    # ==================== HELPERS INTERNOS ====================
    
    def _get_cuentas_efectivo_config(self) -> Dict:
        """Obtiene configuración de cuentas de efectivo."""
        return self.mapeo_cuentas.get("cuentas_efectivo", {})
    
    def _get_actividad_nombre(self, key: str) -> str:
        """Retorna el nombre completo de una actividad."""
        nombres = {
            "OPERACION": "1. Flujos de efectivo procedentes (utilizados) en actividades de operación",
            "INVERSION": "2. Flujos de efectivo procedentes de (utilizados) en actividades de inversión",
            "FINANCIAMIENTO": "3. Flujos de efectivo procedentes de (utilizados) en actividades de financiamiento"
        }
        return nombres.get(key, key)
    
    def _parse_odoo_month(self, odoo_month: str) -> str:
        """Parsea el formato de mes de Odoo ('Enero 2026' o '2026-01') a 'YYYY-MM'."""
        if not odoo_month:
            return None
            
        # Si ya está en formato YYYY-MM, devolverlo directamente
        if len(odoo_month) == 7 and odoo_month[4] == '-':
            return odoo_month
            
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
    
    def _parse_odoo_week(self, odoo_week: str) -> str:
        """Parsea el formato de semana de Odoo ('W01 2026') a '2026-W01'."""
        if not odoo_week:
            return None
        try:
            parts = odoo_week.split(' ')
            if len(parts) == 2:
                week_str = parts[0]  # W01
                year_str = parts[1]  # 2026
                return f"{year_str}-{week_str}"
        except:
            pass
        return odoo_week
    
    def _generar_periodos(self, fecha_inicio: str, fecha_fin: str, 
                          agrupacion: str = 'mensual') -> List[str]:
        """Genera lista de períodos en el rango."""
        fecha_ini_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d')
        fecha_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d')
        
        periodos = []
        
        if agrupacion == 'semanal':
            current = fecha_ini_dt
            while current <= fecha_fin_dt:
                y, w, d = current.isocalendar()
                periodo_str = f"{y}-W{w:02d}"
                if periodo_str not in periodos:
                    periodos.append(periodo_str)
                current += timedelta(days=1)
        else:
            current = fecha_ini_dt.replace(day=1)
            while current <= fecha_fin_dt:
                periodos.append(current.strftime("%Y-%m"))
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1)
                else:
                    current = current.replace(month=current.month + 1)
        
        return periodos
    
    # ==================== FLUJO MENSUALIZADO ====================
    
    def get_flujo_mensualizado(self, fecha_inicio: str, fecha_fin: str, 
                               company_id=None, agrupacion='mensual') -> Dict:
        """
        Genera el Estado de Flujo de Efectivo con granularidad MENSUAL.
        
        Args:
            fecha_inicio: Fecha inicio YYYY-MM-DD
            fecha_fin: Fecha fin YYYY-MM-DD
            company_id: ID de compañía
            agrupacion: 'mensual' o 'semanal'
            
        Returns:
            Flujo estructurado por actividad y mes
        """
        # 1. Generar períodos
        meses_lista = self._generar_periodos(fecha_inicio, fecha_fin, agrupacion)
        
        resultado = {
            "meta": {"version": "3.3", "mode": "mensualizado"},
            "periodo": {"inicio": fecha_inicio, "fin": fecha_fin},
            "generado": datetime.now().isoformat(),
            "meses": meses_lista,
            "actividades": {},
            "conciliacion": {},
            "efectivo_por_mes": {}
        }
        
        # 2. Obtener cuentas de efectivo
        cuentas_config = self._get_cuentas_efectivo_config()
        cuentas_efectivo_ids = self.odoo_manager.get_cuentas_efectivo(cuentas_config)
        
        if not cuentas_efectivo_ids:
            resultado["error"] = "No se encontraron cuentas de efectivo configuradas"
            return resultado
        
        # 3. Efectivo inicial
        fecha_ini_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d')
        fecha_anterior = (fecha_ini_dt - timedelta(days=1)).strftime('%Y-%m-%d')
        efectivo_inicial = self.odoo_manager.get_saldo_efectivo(fecha_anterior, cuentas_efectivo_ids)
        resultado["conciliacion"]["efectivo_inicial"] = round(efectivo_inicial, 0)
        
        # 4. Obtener movimientos
        movimientos, asientos_ids = self.odoo_manager.get_movimientos_efectivo_periodo(
            fecha_inicio, fecha_fin, cuentas_efectivo_ids, company_id, incluir_draft=False
        )
        
        if not asientos_ids:
            for act_key in ["OPERACION", "INVERSION", "FINANCIAMIENTO"]:
                resultado["actividades"][act_key] = {
                    "nombre": self._get_actividad_nombre(act_key),
                    "subtotal_por_mes": {m: 0 for m in meses_lista},
                    "subtotal": 0,
                    "conceptos": []
                }
            return resultado
        
        # 5. Crear agregador
        agregador = AgregadorFlujo(
            clasificador=self._clasificar_cuenta,
            catalogo=self.catalogo,
            meses_lista=meses_lista
        )
        
        # 6. Obtener y procesar contrapartidas
        # ESTRATEGIA HÍBRIDA para evitar DUPLICACIÓN:
        # A) Cuentas generales: flujo de efectivo estándar (contrapartidas)
        # B) Cuentas monitoreadas (CxC 11030101): usa x_studio_fecha_de_pago como criterio
        #    SOLO entran por Query B, NUNCA por Query A
        
        groupby_key = 'date:week' if agrupacion == 'semanal' else 'date:month'
        parse_fn = self._parse_odoo_week if agrupacion == 'semanal' else self._parse_odoo_month
        
        # IMPORTANTE: Solo cuentas CxC (11030xxx) se procesan como monitoreadas con fecha_de_pago
        # Las cuentas de FINANCIAMIENTO (21xxx, 22xxx) se procesan normalmente en Query A
        todas_cuentas_contrapartida = self.cuentas_monitoreadas.get("cuentas_contrapartida", {}).get("codigos", [])
        
        # Filtrar: solo CxC para Query B (cuentas que empiezan con 1103)
        cuentas_cxc_monitoreadas = [c for c in todas_cuentas_contrapartida if c.startswith('1103')]
        
        # Obtener IDs de cuentas CxC monitoreadas PRIMERO (antes de Query A)
        cxc_ids = []
        if cuentas_cxc_monitoreadas:
            try:
                accs = self.odoo_manager.odoo.search_read(
                    'account.account', 
                    [['code', 'in', cuentas_cxc_monitoreadas]], 
                    ['id', 'code']
                )
                cxc_ids = [a['id'] for a in accs]
                print(f"[FlujoCaja] Cuentas CxC monitoreadas: {[a['code'] for a in accs]} -> IDs: {cxc_ids}")
            except Exception as e:
                print(f"[FlujoCaja] Error buscando cuentas CxC: {e}")

        # Query A: Flujo de efectivo para cuentas NO CxC
        # CRÍTICO: Excluir efectivo Y CxC monitoreadas para evitar duplicación
        # Las cuentas de FINANCIAMIENTO (21xxx, 22xxx) se procesan aquí normalmente
        ids_excluir = list(set(cuentas_efectivo_ids + cxc_ids))
        print(f"[FlujoCaja] Query A: Excluyendo {len(ids_excluir)} cuentas (efectivo + CxC)")
        
        grupos = self.odoo_manager.get_contrapartidas_agrupadas_mensual(
            asientos_ids, ids_excluir, agrupacion
        )
        agregador.procesar_grupos_contrapartida(grupos, None, parse_fn)
        
        # Query B: Solo cuentas CxC usando x_studio_fecha_de_pago
        # SOLO estas cuentas usan la fecha de pago acordada como criterio
        if cuentas_cxc_monitoreadas:
            print(f"[FlujoCaja] Query B: Procesando cuentas CxC {cuentas_cxc_monitoreadas} por fecha_de_pago")
            lineas_monitoreadas = self.odoo_manager.get_lineas_cuenta_periodo(
                cuentas_cxc_monitoreadas, fecha_inicio, fecha_fin
            )
            print(f"[FlujoCaja] Query B: Encontradas {len(lineas_monitoreadas)} líneas CxC")
            # Procesar con inversión de signo para CxC
            agregador.procesar_lineas_cxc(lineas_monitoreadas, self._clasificar_cuenta, agrupacion)
        
        # 7. Procesar etiquetas (EXCLUYENDO cuentas CxC que ya se procesaron en Query B)
        try:
            # Obtener account_ids de las cuentas ya procesadas
            _, cuentas_por_concepto = agregador.obtener_resultados()
            account_ids_to_query = set()
            for concepto_id, cuentas in cuentas_por_concepto.items():
                for codigo, cuenta_data in cuentas.items():
                    acc_id = cuenta_data.get('account_id')
                    # EXCLUIR cuentas CxC monitoreadas (ya tienen etiquetas de Query B)
                    if acc_id and acc_id not in cxc_ids:
                        account_ids_to_query.add(acc_id)
            
            if account_ids_to_query:
                grupos_etiquetas = self.odoo_manager.get_etiquetas_por_mes(
                    asientos_ids, list(account_ids_to_query), agrupacion
                )
                agregador.procesar_etiquetas(grupos_etiquetas, parse_fn)
        except Exception as e:
            print(f"[FlujoCaja] Error procesando etiquetas: {e}")
        
        # 8. Procesar cuentas parametrizadas (EXCLUYENDO las CxC monitoreadas que ya se procesaron en Query B)
        try:
            cuentas_parametrizadas = list(self.mapeo_cuentas.get("mapeo_cuentas", {}).keys())
            # Excluir solo cuentas CxC monitoreadas para evitar duplicación
            cuentas_parametrizadas = [c for c in cuentas_parametrizadas if c not in cuentas_cxc_monitoreadas]
            if cuentas_parametrizadas:
                lineas = self.odoo_manager.get_lineas_cuentas_parametrizadas(
                    cuentas_parametrizadas, fecha_inicio, fecha_fin, asientos_ids
                )
                agregador.procesar_lineas_parametrizadas(lineas, self._clasificar_cuenta, agrupacion)
        except Exception as e:
            print(f"[FlujoCaja] Error procesando cuentas parametrizadas: {e}")
        
        # 9. Procesar facturas draft - DESHABILITADO
        # La proyección ahora se maneja en Query B usando payment_state
        # (not_paid, in_payment, partial) en lugar de state='draft'
        # Esto evita duplicación y el problema de "CXC - Cuentas por Cobrar Proyectadas"
        
        # 10. Calcular REAL/PROYECTADO/PPTO para conceptos especiales
        print(f"[FlujoCaja] Calculando REAL/PROYECTADO para conceptos especiales...")
        try:
            real_proyectado_data = self.real_proyectado_calc.calcular_todos(fecha_inicio, fecha_fin, meses_lista)
        except Exception as e:
            print(f"[FlujoCaja] Error calculando REAL/PROYECTADO: {e}")
            real_proyectado_data = {}
        
        # 11. Construir resultado
        conceptos_por_actividad, subtotales_por_actividad = agregador.construir_conceptos_por_actividad()
        
        # Enriquecer conceptos con REAL/PROYECTADO
        for act_key in ["OPERACION", "INVERSION", "FINANCIAMIENTO"]:
            conceptos = conceptos_por_actividad.get(act_key, [])
            for concepto in conceptos:
                concepto_id = concepto.get('id', '')
                self.real_proyectado_calc.enriquecer_concepto(
                    concepto, real_proyectado_data, concepto_id
                )
        
        for act_key in ["OPERACION", "INVERSION", "FINANCIAMIENTO"]:
            subtotal_mes = subtotales_por_actividad[act_key]
            resultado["actividades"][act_key] = {
                "nombre": self._get_actividad_nombre(act_key),
                "subtotal_por_mes": {m: round(subtotal_mes.get(m, 0), 0) for m in meses_lista},
                "subtotal": round(sum(subtotal_mes.values()), 0),
                "conceptos": conceptos_por_actividad[act_key]
            }
        
        # 11. Calcular efectivo por mes
        efectivo_acumulado = efectivo_inicial
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
        """Genera el Estado de Flujo de Efectivo con granularidad SEMANAL."""
        return self.get_flujo_mensualizado(fecha_inicio, fecha_fin, company_id, agrupacion='semanal')
    
    # ==================== FLUJO CONSOLIDADO ====================
    
    def get_flujo_efectivo(self, fecha_inicio: str, fecha_fin: str, 
                           company_id: int = None) -> Dict:
        """
        Genera el Estado de Flujo de Efectivo consolidado para el período.
        Método Directo según NIIF IAS 7.
        """
        resultado = {
            "meta": {"version": "3.3", "mode": "hierarchical"},
            "periodo": {"inicio": fecha_inicio, "fin": fecha_fin},
            "generado": datetime.now().isoformat(),
            "actividades": {},
            "proyeccion": {},
            "conciliacion": {},
            "detalle_movimientos": []
        }
        
        # 1. Obtener cuentas de efectivo
        cuentas_config = self._get_cuentas_efectivo_config()
        cuentas_efectivo_ids = self.odoo_manager.get_cuentas_efectivo(cuentas_config)
        
        if not cuentas_efectivo_ids:
            resultado["error"] = "No se encontraron cuentas de efectivo configuradas"
            return resultado
        
        # 2. Efectivo inicial
        fecha_inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d')
        fecha_anterior = (fecha_inicio_dt - timedelta(days=1)).strftime('%Y-%m-%d')
        efectivo_inicial = self.odoo_manager.get_saldo_efectivo(fecha_anterior, cuentas_efectivo_ids)
        
        # 3. Obtener movimientos
        movimientos, asientos_ids = self.odoo_manager.get_movimientos_efectivo_periodo(
            fecha_inicio, fecha_fin, cuentas_efectivo_ids, company_id
        )
        
        # 4. Agregar contrapartidas
        montos_por_concepto = {c["id"]: 0.0 for c in self.catalogo.get("conceptos", []) if c.get("tipo") == "LINEA"}
        montos_por_concepto[CATEGORIA_NEUTRAL] = 0.0
        cuentas_pendientes = {}
        cuentas_por_concepto = {}
        
        grupos = self.odoo_manager.get_contrapartidas_agrupadas(asientos_ids, cuentas_efectivo_ids)
        
        cuentas_monitoreadas = self.cuentas_monitoreadas.get("cuentas_contrapartida", {}).get("codigos", [])
        filtrar_monitoreadas = len(cuentas_monitoreadas) > 0
        
        for grupo in grupos:
            acc_data = grupo.get('account_id')
            balance = grupo.get('balance', 0)
            count = grupo.get('__count', 1)
            
            if not acc_data:
                continue
            
            acc_display = acc_data[1] if len(acc_data) > 1 else "Unknown"
            codigo_cuenta = acc_display.split(' ')[0] if ' ' in acc_display else acc_display
            nombre_cuenta = ' '.join(acc_display.split(' ')[1:]) if ' ' in acc_display else acc_display
            
            if filtrar_monitoreadas and codigo_cuenta not in cuentas_monitoreadas:
                continue
            
            concepto_id, es_pendiente = self._clasificar_cuenta(codigo_cuenta)
            
            if concepto_id is None:
                continue
            
            if concepto_id == CATEGORIA_NEUTRAL:
                montos_por_concepto[CATEGORIA_NEUTRAL] += balance
            else:
                if concepto_id not in montos_por_concepto:
                    montos_por_concepto[concepto_id] = 0.0
                montos_por_concepto[concepto_id] += balance
            
            # Tracking
            if concepto_id not in cuentas_por_concepto:
                cuentas_por_concepto[concepto_id] = {}
            if codigo_cuenta not in cuentas_por_concepto[concepto_id]:
                cuentas_por_concepto[concepto_id][codigo_cuenta] = {'nombre': nombre_cuenta, 'monto': 0, 'cantidad': 0}
            cuentas_por_concepto[concepto_id][codigo_cuenta]['monto'] += balance
            cuentas_por_concepto[concepto_id][codigo_cuenta]['cantidad'] += count
            
            if es_pendiente:
                if codigo_cuenta not in cuentas_pendientes:
                    cuentas_pendientes[codigo_cuenta] = {'nombre': nombre_cuenta, 'monto': 0, 'cantidad': 0}
                cuentas_pendientes[codigo_cuenta]['monto'] += balance
                cuentas_pendientes[codigo_cuenta]['cantidad'] += count
        
        # 5. Estructurar por actividad
        def calcular_monto_nodo(nodo_id):
            monto_total = 0.0
            prefix = nodo_id + "."
            for c_id, monto in montos_por_concepto.items():
                if c_id == nodo_id or c_id.startswith(prefix):
                    if c_id != CATEGORIA_NEUTRAL:
                        monto_total += monto
            return monto_total
        
        conceptos_por_actividad = {"OPERACION": [], "INVERSION": [], "FINANCIAMIENTO": []}
        subtotales = {"OPERACION": 0.0, "INVERSION": 0.0, "FINANCIAMIENTO": 0.0}
        
        for concepto in self.catalogo.get("conceptos", []):
            c_id = concepto.get("id")
            c_tipo = concepto.get("tipo")
            c_actividad = concepto.get("actividad")
            
            if c_tipo == "LINEA":
                monto_nodo = montos_por_concepto.get(c_id, 0.0)
            else:
                monto_nodo = calcular_monto_nodo(c_id)
            
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
                if c_tipo == "LINEA" and c_actividad in subtotales:
                    subtotales[c_actividad] += monto_nodo
        
        # Construir actividades
        for act_key, act_data in [
            ("OPERACION", {"nombre": "1. Flujos de efectivo procedentes (utilizados) en actividades de operación", "subtotal_nombre": "Flujos de efectivo netos procedentes de (utilizados en) actividades de operación"}),
            ("INVERSION", {"nombre": "2. Flujos de efectivo procedentes de (utilizados) en actividades de inversión", "subtotal_nombre": "Flujos de efectivo netos procedentes de (utilizados en) actividades de inversión"}),
            ("FINANCIAMIENTO", {"nombre": "3. Flujos de efectivo procedentes de (utilizados) en actividades de financiamiento", "subtotal_nombre": "Flujos de efectivo netos procedentes de (utilizados en) actividades de financiamiento"})
        ]:
            resultado["actividades"][act_key] = {
                "nombre": act_data["nombre"],
                "subtotal": round(subtotales[act_key], 0),
                "subtotal_nombre": act_data["subtotal_nombre"],
                "conceptos": conceptos_por_actividad[act_key]
            }
        
        # 6. Conciliación
        variacion_neta = subtotales["OPERACION"] + subtotales["INVERSION"] + subtotales["FINANCIAMIENTO"]
        efecto_tc = montos_por_concepto.get("3.2.3", 0)
        neutral = montos_por_concepto.get(CATEGORIA_NEUTRAL, 0)
        efectivo_final_calculado = efectivo_inicial + variacion_neta + efecto_tc
        
        resultado["conciliacion"] = {
            "incremento_neto": round(variacion_neta, 0),
            "efecto_tipo_cambio": round(efecto_tc, 0),
            "variacion_efectivo": round(variacion_neta + efecto_tc, 0),
            "efectivo_inicial": round(efectivo_inicial, 0),
            "efectivo_final": round(efectivo_final_calculado, 0),
            "neutral": round(neutral, 0)
        }
        
        # 7. Cuentas pendientes
        resultado["cuentas_pendientes"] = sorted(
            [{"codigo": k, **v} for k, v in cuentas_pendientes.items()],
            key=lambda x: abs(x.get('monto', 0)),
            reverse=True
        )[:50]
        
        # 8. Proyección
        try:
            proyeccion = ProyeccionFlujo(self.odoo, self._clasificar_cuenta, ESTRUCTURA_FLUJO)
            resultado["proyeccion"] = proyeccion.calcular_proyeccion(fecha_inicio, fecha_fin, company_id)
        except Exception as e:
            print(f"[FlujoCaja] Error calculando proyección: {e}")
            resultado["proyeccion"] = {"error": str(e)}
        
        # 9. Detalle movimientos (muestra)
        resultado["detalle_movimientos"] = [
            {
                "fecha": mov.get('date'),
                "descripcion": mov.get('name') or mov.get('ref') or '',
                "monto": mov.get('balance', 0),
                "clasificacion": "Ver desglose",
                "contrapartida": mov.get('partner_id')[1] if mov.get('partner_id') else "Varios"
            }
            for mov in movimientos[:100]
        ]
        resultado["total_movimientos"] = len(movimientos)
        
        return resultado
    
    # ==================== UTILIDADES ====================
    
    def get_cuentas_efectivo_detalle(self) -> List[Dict]:
        """Retorna las cuentas de efectivo con su detalle."""
        cuentas_config = self._get_cuentas_efectivo_config()
        cuentas_ids = self.odoo_manager.get_cuentas_efectivo(cuentas_config)
        
        if not cuentas_ids:
            return []
        
        try:
            cuentas = self.odoo.read('account.account', cuentas_ids, ['id', 'code', 'name'])
            return cuentas
        except:
            return []
    
    def validar_flujo(self, flujos_por_linea: Dict, 
                      efectivo_inicial: float, efectivo_final_calculado: float,
                      flujos_por_actividad: Dict = None,
                      efectivo_final_real: float = None) -> Dict:
        """Valida el flujo según reglas financieras."""
        config = self.get_configuracion()
        alertas = []
        errores = []
        
        neutral = flujos_por_linea.get(CATEGORIA_NEUTRAL, 0)
        sin_clasificar = flujos_por_linea.get(CATEGORIA_UNCLASSIFIED, 0)
        
        if abs(neutral) > 1000:
            alertas.append({
                "tipo": "NEUTRAL_NO_CERO",
                "mensaje": f"NEUTRAL debería ser ~$0, pero es ${neutral:,.0f}",
                "impacto": neutral
            })
        
        if efectivo_final_real is not None:
            diferencia = efectivo_final_calculado - efectivo_final_real
            if abs(diferencia) > 100:
                alertas.append({
                    "tipo": "RECONCILIACION_DIFERENCIA",
                    "mensaje": f"Diferencia de ${diferencia:,.0f} entre calculado y real",
                    "diferencia": diferencia
                })
        
        return {
            "valido": len(errores) == 0,
            "alertas": alertas,
            "errores": errores,
            "modo_estricto": config.get("modo_estricto", False)
        }
