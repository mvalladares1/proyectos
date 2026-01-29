"""
Servicio para gestionar aprobaciones de órdenes de compra de fletes/transportes.
Integra datos de Odoo + Sistema de Logística para mostrar comparativas.
"""

from shared.odoo_client import OdooClient
import requests
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta


class AprobacionesFletesService:
    """Servicio para aprobaciones de OC de fletes con datos consolidados"""
    
    API_LOGISTICA = "https://riofuturoprocesos.com/api/logistica"
    
    def __init__(self, username: str, password: str):
        self.odoo = OdooClient(username=username, password=password)
        self.username = username
    
    def _determinar_tipo_vehiculo(self, cantidad_kg: float, costo: float) -> str:
        """Determina el tipo de vehículo más probable basado en cantidad y costo"""
        if cantidad_kg == 0:
            # Basarse solo en costo
            if costo < 150000:
                return "Camión 8T"
            elif costo < 400000:
                return "Camión 12-14T"
            elif costo < 600000:
                return "Rampla Corta"
            else:
                return "Rampla"
        else:
            # Basarse en capacidad (kg)
            if cantidad_kg <= 8000:
                return "Camión 8T"
            elif cantidad_kg <= 14000:
                return "Camión 12-14T"
            elif cantidad_kg <= 20000:
                return "Rampla Corta"
            else:
                return "Rampla"
    
    def _match_ruta_con_presupuesto(self, distancia_km: float, tipo_vehiculo: str, costos_maestro: List[Dict]) -> Optional[Dict]:
        """Intenta hacer match de una ruta con el maestro de costos presupuestados"""
        if not costos_maestro or distancia_km == 0:
            return None
        
        # Buscar rutas con distancia similar (±20%)
        margen = 0.20
        km_min = distancia_km * (1 - margen)
        km_max = distancia_km * (1 + margen)
        
        candidatos = []
        for costo in costos_maestro:
            try:
                km_presupuesto = float(costo.get('kilometers', 0))
                if km_min <= km_presupuesto <= km_max:
                    candidatos.append(costo)
            except (ValueError, TypeError):
                continue
        
        if not candidatos:
            return None
        
        # Si hay varios candidatos, tomar el más cercano en distancia
        candidatos.sort(key=lambda x: abs(float(x.get('kilometers', 0)) - distancia_km))
        return candidatos[0]
    
    def _obtener_costo_presupuestado(self, ruta_presupuesto: Dict, tipo_vehiculo: str) -> Optional[float]:
        """Obtiene el costo presupuestado según el tipo de vehículo"""
        if not ruta_presupuesto:
            return None
        
        # Mapeo de tipo de vehículo a campo en maestro
        campo_map = {
            'Camión 8T': 'truck_8_cost',
            'Camión 12-14T': 'truck_12_14_cost',
            'Rampla Corta': 'short_rampla_cost',
            'Rampla': 'rampla_cost'
        }
        
        campo = campo_map.get(tipo_vehiculo)
        if campo:
            costo = ruta_presupuesto.get(campo)
            if costo and costo > 0:
                return float(costo)
        
        # Si no hay costo para ese tipo, intentar con otros tipos en orden
        for campo in ['truck_8_cost', 'truck_12_14_cost', 'short_rampla_cost', 'rampla_cost']:
            costo = ruta_presupuesto.get(campo)
            if costo and costo > 0:
                return float(costo)
        
        return None
    
    def get_ocs_pendientes_aprobacion(self) -> List[Dict[str, Any]]:
        """
        Obtiene OCs de TRANSPORTES + SERVICIOS pendientes de aprobación de Máximo.
        Solo trae OCs en estado 'to approve' con activity asignada a Máximo.
        """
        # Buscar ID de Máximo Sepúlveda
        usuarios = self.odoo.search_read(
            'res.users',
            [('login', 'ilike', 'msepulveda')],
            ['id', 'name', 'login'],
            limit=1
        )
        
        if not usuarios:
            print("⚠️ No se encontró usuario Máximo Sepúlveda")
            return []
        
        maximo_id = usuarios[0]['id']
        print(f"✅ Usuario Máximo encontrado: ID {maximo_id} - {usuarios[0]['name']}")
        
        # Buscar OCs pendientes
        domain = [
            ('state', 'in', ['to approve', 'sent']),  # Estados pendientes de aprobación
            ('x_studio_selection_field_yUNPd', '=', 'TRANSPORTES'),
            ('x_studio_categora_de_producto', '=', 'SERVICIOS'),
        ]
        
        campos = [
            'id', 'name', 'partner_id', 'amount_total', 'currency_id',
            'state', 'date_order', 'user_id', 'origin',
            'x_studio_selection_field_yUNPd',
            'x_studio_categora_de_producto',
            'notes',  # Puede contener info de la ruta
        ]
        
        ocs = self.odoo.search_read('purchase.order', domain, campos, limit=200)
        
        print(f"📋 OCs de TRANSPORTES + SERVICIOS encontradas: {len(ocs)}")
        
        # Enriquecer con información de líneas
        for oc in ocs:
            oc_id = oc['id']
            
            # Obtener líneas de la OC
            lines = self.odoo.search_read(
                'purchase.order.line',
                [('order_id', '=', oc_id)],
                ['product_id', 'name', 'product_qty', 'price_unit', 'price_subtotal'],
                limit=50
            )
            
            oc['lines'] = lines
        
        return ocs
    
    def get_rutas_logistica(self, con_oc: bool = True) -> List[Dict[str, Any]]:
        """
        Obtiene rutas del sistema de logística.
        
        Args:
            con_oc: Si True, solo retorna rutas con OC generada
        """
        try:
            response = requests.get(f"{self.API_LOGISTICA}/rutas", timeout=90)
            
            if response.status_code == 200:
                rutas = response.json()
                
                if con_oc:
                    rutas = [r for r in rutas if r.get('purchase_order_name')]
                
                return rutas
            else:
                print(f"❌ Error al obtener rutas: {response.status_code}")
                return []
        
        except requests.exceptions.Timeout:
            print(f"⏱️ Timeout al obtener rutas de logística (90s)")
            return []
        except requests.exceptions.ConnectionError as e:
            print(f"🔌 Error de conexión con API logística: {e}")
            return []
        except Exception as e:
            print(f"❌ Error al conectar con API logística: {e}")
            return []
    
    def get_maestro_costos(self) -> List[Dict[str, Any]]:
        """Obtiene el maestro de costos presupuestados de rutas"""
        try:
            response = requests.get(f"{self.API_LOGISTICA}/db/coste-rutas", timeout=90)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Error al obtener costos: {response.status_code}")
                return []
        
        except requests.exceptions.Timeout:
            print(f"⏱️ Timeout al obtener costos de logística (90s)")
            return []
        except requests.exceptions.ConnectionError as e:
            print(f"🔌 Error de conexión con API logística: {e}")
            return []
        except Exception as e:
            print(f"❌ Error al conectar con API logística: {e}")
            return []
    
    def consolidar_datos_aprobacion(self) -> List[Dict[str, Any]]:
        """
        Consolida datos de Odoo + Logística para mostrar en UI de aprobaciones.
        
        Returns:
            Lista de diccionarios con estructura:
            {
                'oc_id': int,
                'oc_name': str,
                'oc_state': str,
                'oc_amount': float,
                'proveedor': str,
                'fecha_orden': str,
                'ruta_id': int,
                'ruta_name': str,
                'ruta_status': str,
                'distancia_km': float,
                'costo_real': float,
                'costo_presupuestado': float,
                'desviacion_pct': float,
                'desviacion_favorable': bool,
                'costo_por_kg': float,
                'vehiculo': str,
                'tiene_info_logistica': bool
            }
        """
        # 1. Obtener OCs pendientes
        ocs = self.get_ocs_pendientes_aprobacion()
        
        # 2. Obtener rutas con OC
        rutas = self.get_rutas_logistica(con_oc=True)
        
        # 3. Obtener maestro de costos
        costos_maestro = self.get_maestro_costos()
        
        # 4. Crear mapa de rutas por nombre de OC
        rutas_map = {}
        for ruta in rutas:
            oc_name = ruta.get('purchase_order_name')
            if oc_name:
                rutas_map[oc_name] = ruta
        
        # 5. Consolidar datos
        datos_consolidados = []
        
        for oc in ocs:
            oc_name = oc.get('name', '')
            ruta = rutas_map.get(oc_name)
            
            # Determinar tipo de vehículo si hay ruta
            tipo_vehiculo = None
            if ruta:
                cantidad_kg = ruta.get('total_qnt', 0)
                costo_real = ruta.get('total_cost', 0)
                tipo_vehiculo = self._determinar_tipo_vehiculo(cantidad_kg, costo_real)
            
            # Buscar costo presupuestado
            costo_presupuestado = None
            ruta_presupuesto = None
            desviacion_pct = None
            desviacion_favorable = None
            
            if ruta and tipo_vehiculo:
                distancia_km = ruta.get('total_distance_km', 0)
                ruta_presupuesto = self._match_ruta_con_presupuesto(distancia_km, tipo_vehiculo, costos_maestro)
                
                if ruta_presupuesto:
                    costo_presupuestado = self._obtener_costo_presupuestado(ruta_presupuesto, tipo_vehiculo)
                    
                    # Calcular desviación
                    if costo_presupuestado and costo_presupuestado > 0:
                        costo_real = ruta.get('total_cost', 0)
                        if costo_real > 0:
                            desviacion_pct = ((costo_real - costo_presupuestado) / costo_presupuestado) * 100
                            desviacion_favorable = desviacion_pct <= 0  # Favorable si gastamos menos
            
            item = {
                # Datos de OC (Odoo)
                'oc_id': oc['id'],
                'oc_name': oc_name,
                'oc_url': f"https://riofuturo.server98c6e.oerpondemand.net/web#id={oc['id']}&model=purchase.order&view_type=form",
                'oc_state': oc.get('state', ''),
                'oc_amount': oc.get('amount_total', 0),
                'currency': oc.get('currency_id', [False, 'CLP'])[1] if oc.get('currency_id') else 'CLP',
                'proveedor': oc.get('partner_id', [False, 'N/A'])[1] if oc.get('partner_id') else 'N/A',
                'fecha_orden': oc.get('date_order', ''),
                'usuario_creador': oc.get('user_id', [False, 'N/A'])[1] if oc.get('user_id') else 'N/A',
                'origin': oc.get('origin', ''),
                'lines': oc.get('lines', []),
                
                # Datos de ruta (Sistema Logística)
                'tiene_info_logistica': ruta is not None,
                'ruta_id': ruta.get('id') if ruta else None,
                'ruta_name': ruta.get('name') if ruta else None,
                'ruta_status': ruta.get('status') if ruta else None,
                'distancia_km': ruta.get('total_distance_km', 0) if ruta else 0,
                'costo_real': ruta.get('total_cost', 0) if ruta else 0,
                'costo_ruta_negociado': ruta.get('route_cost', 0) if ruta else 0,
                'costo_por_km': ruta.get('cost_per_km', 0) if ruta else 0,
                'costo_por_kg': ruta.get('cost_per_kg', 0) if ruta else 0,
                'cantidad_kg': ruta.get('total_qnt', 0) if ruta else 0,
                'carrier_id': ruta.get('carrier_id') if ruta else None,
                'estimated_date': ruta.get('estimated_date') if ruta else None,
                'tipo_vehiculo': tipo_vehiculo,
                
                # Análisis de desviación
                'costo_presupuestado': costo_presupuestado,
                'desviacion_pct': round(desviacion_pct, 2) if desviacion_pct is not None else None,
                'desviacion_favorable': desviacion_favorable,
                'ruta_presupuesto_nombre': ruta_presupuesto.get('route_name') if ruta_presupuesto else None,
                'ruta_presupuesto_km': float(ruta_presupuesto.get('kilometers', 0)) if ruta_presupuesto else None,
            }
            
            datos_consolidados.append(item)
        
        return datos_consolidados
    
    def aprobar_oc(self, oc_id: int) -> bool:
        """
        Aprueba una orden de compra cambiando su estado.
        """
        try:
            # Cambiar estado a 'purchase' (aprobada)
            self.odoo.execute(
                'purchase.order',
                'button_confirm',
                [oc_id]
            )
            print(f"✅ OC ID {oc_id} aprobada correctamente")
            return True
        
        except Exception as e:
            print(f"❌ Error al aprobar OC {oc_id}: {e}")
            return False
    
    def aprobar_multiples_ocs(self, oc_ids: List[int]) -> Dict[str, Any]:
        """
        Aprueba múltiples OCs y retorna resumen de resultados.
        """
        aprobadas = []
        fallidas = []
        
        for oc_id in oc_ids:
            if self.aprobar_oc(oc_id):
                aprobadas.append(oc_id)
            else:
                fallidas.append(oc_id)
        
        return {
            'total': len(oc_ids),
            'aprobadas': len(aprobadas),
            'fallidas': len(fallidas),
            'oc_ids_aprobadas': aprobadas,
            'oc_ids_fallidas': fallidas
        }
    
    def get_kpis_fletes(self, dias: int = 30) -> Dict[str, Any]:
        """
        Calcula KPIs de órdenes de fletes en los últimos N días.
        """
        fecha_desde = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')
        
        domain = [
            ('date_order', '>=', fecha_desde),
            ('x_studio_selection_field_yUNPd', '=', 'TRANSPORTES'),
            ('x_studio_categora_de_producto', '=', 'SERVICIOS'),
        ]
        
        ocs = self.odoo.search_read(
            'purchase.order',
            domain,
            ['id', 'name', 'state', 'amount_total', 'date_order'],
            limit=500
        )
        
        total_ocs = len(ocs)
        pendientes = len([oc for oc in ocs if oc['state'] in ['to approve', 'sent', 'draft']])
        aprobadas = len([oc for oc in ocs if oc['state'] in ['purchase', 'done']])
        canceladas = len([oc for oc in ocs if oc['state'] == 'cancel'])
        
        monto_total = sum([oc.get('amount_total', 0) for oc in ocs])
        monto_aprobado = sum([oc.get('amount_total', 0) for oc in ocs if oc['state'] in ['purchase', 'done']])
        
        return {
            'periodo_dias': dias,
            'total_ocs': total_ocs,
            'pendientes': pendientes,
            'aprobadas': aprobadas,
            'canceladas': canceladas,
            'monto_total': monto_total,
            'monto_aprobado': monto_aprobado,
            'promedio_por_oc': monto_total / total_ocs if total_ocs > 0 else 0,
        }
