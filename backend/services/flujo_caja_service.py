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
    
    def __init__(self, username: str = None, password: str = None):
        self.odoo = OdooClient(username=username, password=password)
        self.mapeo_cuentas = self._cargar_mapeo()
        self._cache_cuentas_efectivo = None
    
    def _cargar_mapeo(self) -> Dict:
        """Carga el mapeo de cuentas desde archivo JSON."""
        mapeo_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 'data', 'mapeo_flujo_caja.json'
        )
        try:
            if os.path.exists(mapeo_path):
                with open(mapeo_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"[FlujoCaja] Error cargando mapeo: {e}")
        
        return self._mapeo_default()
    
    def _mapeo_default(self) -> Dict:
        """Retorna mapeo por defecto basado en plan de cuentas típico chileno."""
        return {
            # Cuentas de efectivo y equivalentes (códigos que empiezan con 110, 111)
            "cuentas_efectivo": {
                "prefijos": ["110", "111", "1101", "1102", "1103"],
                "codigos_especificos": []
            },
            # Mapeo de cuentas a líneas del flujo
            "mapeo_lineas": {
                # Operación
                "OP01": {"prefijos": ["410", "411", "412"], "descripcion": "Ingresos por ventas"},
                "OP02": {"prefijos": ["510", "511", "512", "210", "211"], "descripcion": "Pagos a proveedores"},
                "OP03": {"prefijos": ["620", "621", "622", "623", "215"], "descripcion": "Remuneraciones"},
                "OP04": {"prefijos": ["650", "651"], "descripcion": "Intereses pagados"},
                "OP05": {"prefijos": ["420", "421"], "descripcion": "Intereses recibidos"},
                "OP06": {"prefijos": ["640", "641", "216"], "descripcion": "Impuestos"},
                "OP07": {"prefijos": [], "descripcion": "Otros operacionales"},
                # Inversión
                "IN03": {"prefijos": ["123", "124", "125"], "descripcion": "PPE"},
                "IN04": {"prefijos": ["126", "127"], "descripcion": "Intangibles"},
                "IN05": {"prefijos": ["422"], "descripcion": "Dividendos recibidos"},
                "IN06": {"prefijos": ["430"], "descripcion": "Venta activos"},
                # Financiamiento
                "FI01": {"prefijos": ["230", "231"], "descripcion": "Préstamos LP"},
                "FI02": {"prefijos": ["220", "221"], "descripcion": "Préstamos CP"},
                "FI03": {"prefijos": ["232", "233"], "descripcion": "Préstamos relacionadas"},
                "FI04": {"prefijos": ["230", "231"], "descripcion": "Pago préstamos"},
                "FI07": {"prefijos": ["310", "311"], "descripcion": "Dividendos pagados"},
            }
        }
    
    def guardar_mapeo(self, mapeo: Dict) -> bool:
        """Guarda el mapeo de cuentas en archivo JSON."""
        mapeo_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 'data', 'mapeo_flujo_caja.json'
        )
        try:
            os.makedirs(os.path.dirname(mapeo_path), exist_ok=True)
            with open(mapeo_path, 'w', encoding='utf-8') as f:
                json.dump(mapeo, f, indent=2, ensure_ascii=False)
            self.mapeo_cuentas = mapeo
            return True
        except Exception as e:
            print(f"[FlujoCaja] Error guardando mapeo: {e}")
            return False
    
    def _get_cuentas_efectivo(self) -> List[int]:
        """Obtiene IDs de cuentas clasificadas como efectivo y equivalentes."""
        if self._cache_cuentas_efectivo:
            return self._cache_cuentas_efectivo
        
        # Buscar cuentas que coincidan con prefijos de efectivo
        prefijos = self.mapeo_cuentas.get("cuentas_efectivo", {}).get("prefijos", ["110", "111"])
        
        # Construir dominio OR para todos los prefijos
        domain = ['|'] * (len(prefijos) - 1) if len(prefijos) > 1 else []
        for prefijo in prefijos:
            domain.append(['code', '=like', f'{prefijo}%'])
        
        if not domain:
            domain = [['code', '=like', '110%']]
        
        try:
            cuentas = self.odoo.search_read(
                'account.account',
                domain,
                ['id', 'code', 'name'],
                limit=100
            )
            self._cache_cuentas_efectivo = [c['id'] for c in cuentas]
            return self._cache_cuentas_efectivo
        except Exception as e:
            print(f"[FlujoCaja] Error obteniendo cuentas efectivo: {e}")
            return []
    
    def _clasificar_cuenta(self, codigo_cuenta: str) -> Optional[str]:
        """Clasifica una cuenta según el mapeo y retorna el código de línea."""
        mapeo_lineas = self.mapeo_cuentas.get("mapeo_lineas", {})
        
        for linea_codigo, config in mapeo_lineas.items():
            prefijos = config.get("prefijos", [])
            for prefijo in prefijos:
                if codigo_cuenta.startswith(prefijo):
                    return linea_codigo
        
        return None
    
    def _get_saldo_efectivo(self, fecha: str, cuentas_efectivo_ids: List[int]) -> float:
        """Calcula el saldo de efectivo a una fecha dada."""
        if not cuentas_efectivo_ids:
            return 0.0
        
        try:
            # Buscar todos los movimientos hasta la fecha
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
        except Exception as e:
            print(f"[FlujoCaja] Error calculando saldo efectivo: {e}")
            return 0.0
    
    def get_flujo_efectivo(self, fecha_inicio: str, fecha_fin: str, 
                           company_id: int = None) -> Dict:
        """
        Genera el Estado de Flujo de Efectivo para el período indicado.
        
        Método Directo: Analiza movimientos en cuentas de efectivo y clasifica
        según la contrapartida del asiento.
        """
        resultado = {
            "periodo": {"inicio": fecha_inicio, "fin": fecha_fin},
            "generado": datetime.now().isoformat(),
            "actividades": {},
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
        
        # Obtener todas las líneas de los asientos para identificar contrapartidas
        contrapartidas = {}
        if asientos_ids:
            try:
                todas_lineas = self.odoo.search_read(
                    'account.move.line',
                    [['move_id', 'in', asientos_ids]],
                    ['id', 'move_id', 'account_id', 'debit', 'credit', 'balance'],
                    limit=100000
                )
                
                # Agrupar por asiento
                for linea in todas_lineas:
                    move_id = linea['move_id'][0] if isinstance(linea.get('move_id'), (list, tuple)) else linea.get('move_id')
                    if move_id not in contrapartidas:
                        contrapartidas[move_id] = []
                    contrapartidas[move_id].append(linea)
            except Exception as e:
                print(f"[FlujoCaja] Error obteniendo contrapartidas: {e}")
        
        # Obtener info de cuentas para clasificación
        cuentas_info = {}
        cuenta_ids_all = list(set(
            l['account_id'][0] if isinstance(l.get('account_id'), (list, tuple)) else l.get('account_id')
            for lineas in contrapartidas.values() for l in lineas if l.get('account_id')
        ))
        
        if cuenta_ids_all:
            try:
                cuentas = self.odoo.read('account.account', cuenta_ids_all, ['id', 'code', 'name'])
                cuentas_info = {c['id']: c for c in cuentas}
            except:
                pass
        
        # 5. Clasificar cada movimiento
        flujos_por_linea = {
            linea["codigo"]: 0.0 
            for cat in ESTRUCTURA_FLUJO.values() 
            for linea in cat["lineas"]
        }
        flujos_por_linea["OTROS"] = 0.0  # Para movimientos no clasificados
        
        detalle = []
        
        for mov in movimientos_efectivo:
            move_id = mov['move_id'][0] if isinstance(mov.get('move_id'), (list, tuple)) else mov.get('move_id')
            account_id = mov['account_id'][0] if isinstance(mov.get('account_id'), (list, tuple)) else mov.get('account_id')
            monto = mov.get('balance', 0)  # Positivo = entrada, negativo = salida
            
            # Buscar contrapartida (línea con signo opuesto en el mismo asiento)
            lineas_asiento = contrapartidas.get(move_id, [])
            contrapartida_cuenta = None
            
            for linea in lineas_asiento:
                linea_account_id = linea['account_id'][0] if isinstance(linea.get('account_id'), (list, tuple)) else linea.get('account_id')
                # La contrapartida es la cuenta que NO es de efectivo
                if linea_account_id not in cuentas_efectivo_ids:
                    contrapartida_cuenta = cuentas_info.get(linea_account_id, {})
                    break
            
            # Clasificar según la contrapartida
            codigo_linea = "OTROS"
            if contrapartida_cuenta:
                codigo_cuenta = contrapartida_cuenta.get('code', '')
                clasificacion = self._clasificar_cuenta(codigo_cuenta)
                if clasificacion:
                    codigo_linea = clasificacion
            
            # Acumular
            flujos_por_linea[codigo_linea] = flujos_por_linea.get(codigo_linea, 0) + monto
            
            # Guardar detalle
            detalle.append({
                "fecha": mov.get('date'),
                "descripcion": mov.get('name') or mov.get('ref') or '',
                "monto": monto,
                "clasificacion": codigo_linea,
                "contrapartida": contrapartida_cuenta.get('name', '') if contrapartida_cuenta else ''
            })
        
        # 6. Estructurar resultado
        for cat_key, cat_data in ESTRUCTURA_FLUJO.items():
            lineas_resultado = []
            subtotal = 0.0
            
            for linea in cat_data["lineas"]:
                monto = flujos_por_linea.get(linea["codigo"], 0)
                subtotal += monto
                lineas_resultado.append({
                    "codigo": linea["codigo"],
                    "nombre": linea["nombre"],
                    "monto": round(monto, 0)
                })
            
            resultado["actividades"][cat_key] = {
                "nombre": cat_data["nombre"],
                "lineas": lineas_resultado,
                "subtotal": round(subtotal, 0),
                "subtotal_nombre": cat_data["subtotal"]
            }
        
        # 7. Conciliación
        flujo_operacion = resultado["actividades"]["OPERACION"]["subtotal"]
        flujo_inversion = resultado["actividades"]["INVERSION"]["subtotal"]
        flujo_financiamiento = resultado["actividades"]["FINANCIAMIENTO"]["subtotal"]
        otros = flujos_por_linea.get("OTROS", 0)
        
        variacion_neta = flujo_operacion + flujo_inversion + flujo_financiamiento + otros
        efectivo_final = efectivo_inicial + variacion_neta
        
        resultado["conciliacion"] = {
            "incremento_neto": round(variacion_neta, 0),
            "efecto_tipo_cambio": 0,  # TODO: Implementar si hay multimoneda
            "variacion_efectivo": round(variacion_neta, 0),
            "efectivo_inicial": round(efectivo_inicial, 0),
            "efectivo_final": round(efectivo_final, 0),
            "otros_no_clasificados": round(otros, 0)
        }
        
        resultado["detalle_movimientos"] = detalle[:100]  # Limitar detalle
        resultado["total_movimientos"] = len(detalle)
        
        return resultado
    
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
