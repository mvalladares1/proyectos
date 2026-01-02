"""
Servicio de Flujo de Caja - Estado de Flujo de Efectivo NIIF IAS 7 (Método Directo)

Este servicio genera el Estado de Flujo de Efectivo obteniendo datos desde Odoo.
El flujo se construye exclusivamente desde movimientos que afectan cuentas de efectivo.
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import os

from shared.odoo_client import OdooClient


# Estructura del Estado de Flujo de Efectivo según NIIF IAS 7
ESTRUCTURA_FLUJO = {
    "OPERACION": {
        "nombre": "ACTIVIDADES DE OPERACIÓN",
        "lineas": [
            {"codigo": "OP01", "nombre": "Cobros procedentes de las ventas de bienes y prestación de servicios", "signo": 1},
            {"codigo": "OP02", "nombre": "Pagos a proveedores por el suministro de bienes y servicios", "signo": -1},
            {"codigo": "OP03", "nombre": "Pagos a y por cuenta de los empleados", "signo": -1},
            {"codigo": "OP04", "nombre": "Intereses pagados", "signo": -1},
            {"codigo": "OP05", "nombre": "Intereses recibidos", "signo": 1},
            {"codigo": "OP06", "nombre": "Impuestos a las ganancias reembolsados (pagados)", "signo": -1},
            {"codigo": "OP07", "nombre": "Otras entradas (salidas) de efectivo", "signo": 1},
        ],
        "subtotal": "Flujos de efectivo netos procedentes de (utilizados en) actividades de operación"
    },
    "INVERSION": {
        "nombre": "ACTIVIDADES DE INVERSIÓN",
        "lineas": [
            {"codigo": "IN01", "nombre": "Flujos de efectivo utilizados para obtener el control de subsidiarias u otros negocios", "signo": -1},
            {"codigo": "IN02", "nombre": "Flujos de efectivo utilizados en la compra de participaciones no controladoras", "signo": -1},
            {"codigo": "IN03", "nombre": "Compras de propiedades, planta y equipo", "signo": -1},
            {"codigo": "IN04", "nombre": "Compras de activos intangibles", "signo": -1},
            {"codigo": "IN05", "nombre": "Dividendos recibidos", "signo": 1},
            {"codigo": "IN06", "nombre": "Ventas de propiedades, planta y equipo", "signo": 1},
        ],
        "subtotal": "Flujos de efectivo netos procedentes de (utilizados en) actividades de inversión"
    },
    "FINANCIAMIENTO": {
        "nombre": "ACTIVIDADES DE FINANCIAMIENTO",
        "lineas": [
            {"codigo": "FI01", "nombre": "Importes procedentes de préstamos de largo plazo", "signo": 1},
            {"codigo": "FI02", "nombre": "Importes procedentes de préstamos de corto plazo", "signo": 1},
            {"codigo": "FI03", "nombre": "Préstamos de entidades relacionadas", "signo": 1},
            {"codigo": "FI04", "nombre": "Pagos de préstamos", "signo": -1},
            {"codigo": "FI05", "nombre": "Pagos de préstamos a entidades relacionadas", "signo": -1},
            {"codigo": "FI06", "nombre": "Pagos de pasivos por arrendamientos financieros", "signo": -1},
            {"codigo": "FI07", "nombre": "Dividendos pagados", "signo": -1},
        ],
        "subtotal": "Flujos de efectivo netos procedentes de (utilizados en) actividades de financiamiento"
    }
}


class FlujoCajaService:
    """Servicio para generar Estado de Flujo de Efectivo NIIF IAS 7."""
    
    # Categorías técnicas especiales
    CATEGORIA_NEUTRAL = "NEUTRAL"       # No impacta flujo (transferencias internas)
    CATEGORIA_FX_EFFECT = "FX_EFFECT"   # Diferencia tipo de cambio
    CATEGORIA_UNCLASSIFIED = "UNCLASSIFIED"  # Sin clasificar
    
    def __init__(self, username: str = None, password: str = None):
        self.odoo = OdooClient(username=username, password=password)
        self.mapeo_cuentas = self._cargar_mapeo()
        self._cache_cuentas_efectivo = None
    
    def _get_mapeo_path(self) -> str:
        """Retorna la ruta al archivo de mapeo."""
        return os.path.join(
            os.path.dirname(__file__), 
            '..', 'data', 'mapeo_cuentas.json'
        )
    
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
            "version": "2.0",
            "cuentas_efectivo": {
                "prefijos": ["110", "111", "1101", "1102", "1103"],
                "codigos_especificos": []
            },
            "categorias": {},
            "mapeo_cuentas": {}
        }
    
    def _clasificar_cuenta_explicita(self, codigo_cuenta: str) -> str:
        """
        Clasifica una cuenta usando mapeo explícito por código.
        Retorna la categoría o UNCLASSIFIED si no está mapeada.
        """
        mapeo = self.mapeo_cuentas.get("mapeo_cuentas", {})
        
        # Buscar por código exacto
        if codigo_cuenta in mapeo:
            cuenta_info = mapeo[codigo_cuenta]
            if isinstance(cuenta_info, dict):
                return cuenta_info.get("categoria", self.CATEGORIA_UNCLASSIFIED)
            elif isinstance(cuenta_info, str):
                return cuenta_info
        
        return self.CATEGORIA_UNCLASSIFIED
    
    def guardar_mapeo_cuenta(self, codigo: str, categoria: str, nombre: str = "", 
                                usuario: str = "system", impacto_estimado: float = None) -> bool:
        """Guarda o actualiza el mapeo de una cuenta individual con audit trail."""
        mapeo_path = self._get_mapeo_path()
        try:
            # Cargar mapeo actual
            mapeo = self._cargar_mapeo()
            
            # Obtener categoría anterior para audit
            categoria_anterior = None
            if "mapeo_cuentas" in mapeo and codigo in mapeo["mapeo_cuentas"]:
                cuenta_ant = mapeo["mapeo_cuentas"][codigo]
                if isinstance(cuenta_ant, dict):
                    categoria_anterior = cuenta_ant.get("categoria")
                elif isinstance(cuenta_ant, str):
                    categoria_anterior = cuenta_ant
            
            # Actualizar cuenta
            if "mapeo_cuentas" not in mapeo:
                mapeo["mapeo_cuentas"] = {}
            
            mapeo["mapeo_cuentas"][codigo] = {
                "categoria": categoria,
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
                "accion": "actualizar" if categoria_anterior else "crear",
                "cuenta": codigo,
                "nombre_cuenta": nombre,
                "categoria_anterior": categoria_anterior,
                "categoria_nueva": categoria,
                "impacto_estimado": impacto_estimado  # Informativo
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
        
        # 3. Obtener todos los movimientos de efectivo del período
        domain = [
            ['account_id', 'in', cuentas_efectivo_ids],
            ['parent_state', '=', 'posted'],
            ['date', '>=', fecha_inicio],
            ['date', '<=', fecha_fin]
        ]
        if company_id:
            domain.append(['company_id', '=', company_id])
        
        try:
            movimientos_efectivo = self.odoo.search_read(
                'account.move.line',
                domain,
                ['id', 'move_id', 'account_id', 'debit', 'credit', 'balance', 
                 'date', 'name', 'ref', 'partner_id'],
                limit=50000,
                order='date asc'
            )
        except Exception as e:
            resultado["error"] = f"Error obteniendo movimientos: {e}"
            return resultado
        
        # 4. Para cada movimiento, obtener contrapartida y clasificar
        # Agrupar por asiento (move_id)
        asientos_ids = list(set(
            m['move_id'][0] if isinstance(m.get('move_id'), (list, tuple)) else m.get('move_id')
            for m in movimientos_efectivo if m.get('move_id')
        ))
        
        # OPTIMIZADO: Obtener solo líneas de contrapartida (NO cuentas de efectivo)
        # Esto reduce significativamente la cantidad de datos transferidos
        contrapartidas = {}
        if asientos_ids:
            try:
                # Filtrar las cuentas de efectivo directamente en la consulta
                domain = [
                    ['move_id', 'in', asientos_ids],
                    ['account_id', 'not in', cuentas_efectivo_ids]  # Solo contrapartidas
                ]
                
                # OPTIMIZADO: Solo campos necesarios para clasificación
                lineas_contrapartida = self.odoo.search_read(
                    'account.move.line',
                    domain,
                    ['move_id', 'account_id'],  # Solo lo mínimo necesario
                    limit=100000
                )
                
                # Agrupar por asiento (más eficiente con dict.setdefault)
                for linea in lineas_contrapartida:
                    move_id = linea['move_id'][0] if isinstance(linea.get('move_id'), (list, tuple)) else linea.get('move_id')
                    contrapartidas.setdefault(move_id, []).append(linea)
            except Exception as e:
                print(f"[FlujoCaja] Error obteniendo contrapartidas: {e}")
        
        # OPTIMIZADO: Obtener info de cuentas - solo las de contrapartidas
        cuentas_info = {}
        cuenta_ids_all = list(set(
            l['account_id'][0] if isinstance(l.get('account_id'), (list, tuple)) else l.get('account_id')
            for lineas in contrapartidas.values() for l in lineas if l.get('account_id')
        ))
        
        if cuenta_ids_all:
            try:
                # OPTIMIZADO: Solo code (para clasificación) y name (para display)
                cuentas = self.odoo.read('account.account', cuenta_ids_all, ['code', 'name'])
                cuentas_info = {c['id']: c for c in cuentas}
            except:
                pass
        
        # 5. Clasificar cada movimiento
        flujos_por_linea = {
            linea["codigo"]: 0.0 
            for cat in ESTRUCTURA_FLUJO.values() 
            for linea in cat["lineas"]
        }
        # Categorías técnicas
        flujos_por_linea[self.CATEGORIA_NEUTRAL] = 0.0       # No impacta flujo
        flujos_por_linea[self.CATEGORIA_FX_EFFECT] = 0.0     # Diferencia TC
        flujos_por_linea[self.CATEGORIA_UNCLASSIFIED] = 0.0  # Sin clasificar
        
        detalle = []
        cuentas_sin_clasificar = {}  # Para tracking de cuentas UNCLASSIFIED
        
        # DRILL-DOWN: Tracking de cuentas por categoría
        cuentas_por_categoria = {}  # {categoria: {codigo: {nombre, monto, cantidad}}}
        
        def agregar_cuenta_categoria(cat: str, codigo: str, nombre: str, monto: float):
            """Helper para agregar cuenta a tracking de categoría."""
            if cat not in cuentas_por_categoria:
                cuentas_por_categoria[cat] = {}
            if codigo not in cuentas_por_categoria[cat]:
                cuentas_por_categoria[cat][codigo] = {'nombre': nombre, 'monto': 0, 'cantidad': 0}
            cuentas_por_categoria[cat][codigo]['monto'] += monto
            cuentas_por_categoria[cat][codigo]['cantidad'] += 1
        
        for mov in movimientos_efectivo:
            move_id = mov['move_id'][0] if isinstance(mov.get('move_id'), (list, tuple)) else mov.get('move_id')
            monto = mov.get('balance', 0)  # Positivo = entrada, negativo = salida
            
            # OPTIMIZADO: Las contrapartidas ya están filtradas (no incluyen cuentas de efectivo)
            lineas_asiento = contrapartidas.get(move_id, [])
            contrapartida_cuenta = None
            codigo_cuenta = ''
            nombre_cuenta = ''
            
            # Tomar la primera contrapartida (ya está filtrada)
            if lineas_asiento:
                linea = lineas_asiento[0]
                linea_account_id = linea['account_id'][0] if isinstance(linea.get('account_id'), (list, tuple)) else linea.get('account_id')
                contrapartida_cuenta = cuentas_info.get(linea_account_id, {})
                codigo_cuenta = contrapartida_cuenta.get('code', '')
                nombre_cuenta = contrapartida_cuenta.get('name', '')
            
            # Clasificar según la contrapartida (clasificación explícita)
            clasificacion = self._clasificar_cuenta(codigo_cuenta) if codigo_cuenta else self.CATEGORIA_UNCLASSIFIED
            
            # Manejar categorías especiales
            if clasificacion == self.CATEGORIA_NEUTRAL:
                # Transferencias internas: NO impactan el flujo
                flujos_por_linea[self.CATEGORIA_NEUTRAL] += monto
                agregar_cuenta_categoria(self.CATEGORIA_NEUTRAL, codigo_cuenta, nombre_cuenta, monto)
            elif clasificacion == self.CATEGORIA_FX_EFFECT:
                # Diferencia de tipo de cambio: línea separada en conciliación
                flujos_por_linea[self.CATEGORIA_FX_EFFECT] += monto
                agregar_cuenta_categoria(self.CATEGORIA_FX_EFFECT, codigo_cuenta, nombre_cuenta, monto)
            elif clasificacion == self.CATEGORIA_UNCLASSIFIED:
                # Sin clasificar: acumular para diagnóstico
                flujos_por_linea[self.CATEGORIA_UNCLASSIFIED] += monto
                agregar_cuenta_categoria(self.CATEGORIA_UNCLASSIFIED, codigo_cuenta, nombre_cuenta, monto)
                # Trackear cuenta para diagnóstico
                if codigo_cuenta:
                    if codigo_cuenta not in cuentas_sin_clasificar:
                        cuentas_sin_clasificar[codigo_cuenta] = {
                            'nombre': contrapartida_cuenta.get('name', ''),
                            'monto': 0, 'cantidad': 0
                        }
                    cuentas_sin_clasificar[codigo_cuenta]['monto'] += monto
                    cuentas_sin_clasificar[codigo_cuenta]['cantidad'] += 1
            else:
                # Categoría normal (OPxx, INxx, FIxx)
                flujos_por_linea[clasificacion] = flujos_por_linea.get(clasificacion, 0) + monto
                agregar_cuenta_categoria(clasificacion, codigo_cuenta, nombre_cuenta, monto)
            
            # Guardar detalle (limitado para performance)
            if len(detalle) < 100:
                detalle.append({
                    "fecha": mov.get('date'),
                    "descripcion": mov.get('name') or mov.get('ref') or '',
                    "monto": monto,
                    "clasificacion": clasificacion,
                    "contrapartida": contrapartida_cuenta.get('name', '') if contrapartida_cuenta else ''
                })
        
        # 6. Estructurar resultado
        # 6. Estructurar resultado
        for cat_key, cat_data in ESTRUCTURA_FLUJO.items():
            lineas_resultado = []
            conceptos_resultado = []
            subtotal = 0.0
            
            for linea in cat_data["lineas"]:
                codigo = linea["codigo"]
                monto = flujos_por_linea.get(codigo, 0)
                subtotal += monto
                
                # Info básica de línea
                lineas_resultado.append({
                    "codigo": codigo,
                    "nombre": linea["nombre"],
                    "monto": round(monto, 0)
                })
                
                # OPERACION: Construir jerarquía completa (Concepto -> Cuentas)
                if cat_key == "OPERACION":
                    cuentas_concepto = []
                    # Obtener cuentas de esta categoría desde el tracking
                    if codigo in cuentas_por_categoria:
                        cuentas_concepto = sorted(
                            [{"codigo": k, **v} for k, v in cuentas_por_categoria[codigo].items()],
                            key=lambda x: abs(x.get('monto', 0)),
                            reverse=True
                        )
                    
                    conceptos_resultado.append({
                        "codigo": codigo,
                        "nombre": linea["nombre"],
                        "monto": round(monto, 0),
                        "signo": linea.get("signo", 1),
                        "cuentas": cuentas_concepto
                    })
            
            act_result = {
                "nombre": cat_data["nombre"],
                "lineas": lineas_resultado,
                "subtotal": round(subtotal, 0),
                "subtotal_nombre": cat_data["subtotal"]
            }
            
            # Adjuntar jerarquía para Operación
            if cat_key == "OPERACION":
                act_result["conceptos"] = conceptos_resultado
                
            resultado["actividades"][cat_key] = act_result
        
        # 7. Conciliación
        flujo_operacion = resultado["actividades"]["OPERACION"]["subtotal"]
        flujo_inversion = resultado["actividades"]["INVERSION"]["subtotal"]
        flujo_financiamiento = resultado["actividades"]["FINANCIAMIENTO"]["subtotal"]
        
        # Categorías técnicas
        efecto_tc = flujos_por_linea.get(self.CATEGORIA_FX_EFFECT, 0)
        sin_clasificar = flujos_por_linea.get(self.CATEGORIA_UNCLASSIFIED, 0)
        neutral = flujos_por_linea.get(self.CATEGORIA_NEUTRAL, 0)  # NO se suma
        
        # Variación neta: NO incluye NEUTRAL (transferencias internas)
        variacion_neta = flujo_operacion + flujo_inversion + flujo_financiamiento + sin_clasificar
        efectivo_final_calculado = efectivo_inicial + variacion_neta + efecto_tc
        
        resultado["conciliacion"] = {
            "incremento_neto": round(variacion_neta, 0),
            "efecto_tipo_cambio": round(efecto_tc, 0),  # Ahora funcional
            "variacion_efectivo": round(variacion_neta + efecto_tc, 0),
            "efectivo_inicial": round(efectivo_inicial, 0),
            "efectivo_final": round(efectivo_final_calculado, 0),
            "sin_clasificar": round(sin_clasificar, 0),
            "neutral": round(neutral, 0),  # Para debug
            "otros_no_clasificados": round(sin_clasificar, 0)  # Legacy compatibility
        }
        
        # Agregar info de cuentas sin clasificar para el editor
        resultado["cuentas_sin_clasificar"] = sorted(
            [{"codigo": k, **v} for k, v in cuentas_sin_clasificar.items()],
            key=lambda x: abs(x.get('monto', 0)),
            reverse=True
        )[:50]  # Top 50
        
        # DRILL-DOWN: Agregar cuentas por categoría para inspección
        drill_down = {}
        for categoria, cuentas in cuentas_por_categoria.items():
            cuentas_lista = sorted(
                [{"codigo": k, "categoria": categoria, **v} for k, v in cuentas.items()],
                key=lambda x: abs(x.get('monto', 0)),
                reverse=True
            )[:30]  # Top 30 por categoría
            drill_down[categoria] = cuentas_lista
        resultado["drill_down"] = drill_down
        
        # DRILL-DOWN: Detalle de cuentas de efectivo (para efectivo inicial/final)
        cuentas_efectivo_info = []
        for cid in cuentas_efectivo_ids:
            if cid in cuentas_info:
                c = cuentas_info[cid]
                cuentas_efectivo_info.append({
                    "id": cid,
                    "codigo": c.get('code', ''),
                    "nombre": c.get('name', ''),
                    "tipo": "efectivo" if any(c.get('code', '').startswith(p) for p in ["1101", "1102"]) else "equivalente"
                })
        resultado["cuentas_efectivo_detalle"] = cuentas_efectivo_info
        
        # 8. Validaciones
        validacion = self.validar_flujo(
            flujos_por_linea, 
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
        domain = [
            ('move_type', 'in', ['out_invoice', 'in_invoice']),
            ('state', '!=', 'cancel'),  # Excluir cancelados
            ('invoice_date_due', '>=', fecha_inicio),
            ('invoice_date_due', '<=', fecha_fin),
            # Lógica: Draft OR (Posted AND Not Paid)
            '|', ('state', '=', 'draft'), '&', ('state', '=', 'posted'), ('payment_state', '!=', 'paid')
        ]
        
        if company_id:
            domain.append(('company_id', '=', company_id))
            
        campos_move = ['id', 'name', 'ref', 'partner_id', 'invoice_date_due', 'amount_total', 
                       'amount_residual', 'move_type', 'state', 'payment_state']
        
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
        
        campos_lines = ['move_id', 'account_id', 'price_subtotal']
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
                
                # Detalle documento
                entry = {
                    "id": move_id,
                    "documento": move.get('name') or move.get('ref') or str(move_id),
                    "partner": partner_name,
                    "fecha_venc": move.get('invoice_date_due'),
                    "estado": "Borrador" if move.get('state') == 'draft' else "Abierto",
                    "monto": round(monto_parte, 0),
                    "cuenta": acc_code,
                    "tipo": "Factura Cliente" if es_ingreso else "Factura Proveedor"
                }
                
                if categoria == "UNCLASSIFIED":
                    # Agregar a lista especial o manejar en un concepto generico?
                    # Por ahora lo agregamos a detalles_por_concepto bajo llave UNCLASSIFIED
                    # para que luego se pueda exponer
                    pass 
                
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
                
                # Ordenar documentos por fecha vencimiento
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
                "conceptos": conceptos_res
            }
            
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

