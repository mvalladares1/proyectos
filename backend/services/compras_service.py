"""
Servicio de Compras - Gestión de Órdenes de Compra (PO)
Estados de aprobación y recepción.
Optimizado con caché en memoria.
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from functools import lru_cache
import time

from shared.odoo_client import OdooClient


def clean_record(rec: Dict) -> Dict:
    """Limpia registros de Odoo para serialización JSON."""
    out = {}
    for k, v in rec.items():
        if v is False:
            out[k] = None
        elif isinstance(v, (list, tuple)) and len(v) == 2 and isinstance(v[0], int):
            out[k] = v[1]  # Extraer nombre de Many2one
            out[f"{k}_id"] = v[0]
        else:
            out[k] = v
    return out


class ComprasService:
    """Servicio para gestión de Órdenes de Compra."""
    
    # Caché en memoria (simple, se reinicia con el servicio)
    _cache = {}
    _cache_ttl = 300  # 5 minutos
    
    def __init__(self, username: str = None, password: str = None):
        self.odoo = OdooClient(username=username, password=password)
    
    def _get_cache_key(self, prefix: str, *args) -> str:
        return f"{prefix}:{':'.join(str(a) for a in args)}"
    
    def _get_cached(self, key: str) -> Optional[any]:
        if key in self._cache:
            data, timestamp = self._cache[key]
            if time.time() - timestamp < self._cache_ttl:
                return data
            del self._cache[key]
        return None
    
    def _set_cached(self, key: str, data: any):
        self._cache[key] = (data, time.time())
    
    # ============================================================
    #                    ESTADO DE RECEPCIÓN
    # ============================================================
    
    def compute_receive_status(self, po_ids: List[int]) -> Dict[int, str]:
        """
        Calcula el estado de recepción de las POs.
        Retorna: {po_id: 'No recepcionada' | 'Recepción parcial' | 
                         'Recepcionada totalmente' | 'No se recepciona'}
        """
        if not po_ids:
            return {}
        
        # Leer líneas de PO
        try:
            lines = self.odoo.search_read(
                'purchase.order.line',
                [['order_id', 'in', po_ids]],
                ['order_id', 'product_qty', 'qty_received'],
                limit=5000
            )
        except Exception:
            return {pid: "No se recepciona" for pid in po_ids}
        
        # Agrupar líneas por PO
        grouped = {pid: [] for pid in po_ids}
        for line in lines:
            oid = line['order_id'][0] if isinstance(line.get('order_id'), (list, tuple)) else line.get('order_id')
            if oid:
                grouped.setdefault(oid, []).append(line)
        
        result = {}
        
        for pid, lst in grouped.items():
            # Sin líneas → no se recepciona
            if not lst:
                result[pid] = "No se recepciona"
                continue
            
            # Todas las líneas con qty=0 → servicios
            if all(float(l.get('product_qty') or 0) == 0 for l in lst):
                result[pid] = "No se recepciona"
                continue
            
            any_received = False
            fully_received = True
            
            for l in lst:
                ordered = float(l.get('product_qty') or 0)
                received = float(l.get('qty_received') or 0)
                
                if ordered == 0:
                    continue
                
                if received > 0:
                    any_received = True
                
                if received < ordered:
                    fully_received = False
            
            if not any_received:
                result[pid] = "No recepcionada"
            elif fully_received:
                result[pid] = "Recepcionada totalmente"
            else:
                result[pid] = "Recepción parcial"
        
        return result
    
    # ============================================================
    #                    ESTADO DE APROBACIÓN
    # ============================================================
    
    def compute_approval_status(self, po_state: str, approvals_count: int, 
                                required_count: int = None) -> str:
        """Calcula el estado de aprobación de una PO."""
        if po_state == "cancel":
            return "Rechazada"
        
        if po_state in ("purchase", "done"):
            return "Aprobada"
        
        if required_count is None or required_count == 0:
            return "En revisión" if approvals_count == 0 else "Parcialmente aprobada"
        
        if approvals_count == 0:
            return "En revisión"
        elif approvals_count < required_count:
            return "Parcialmente aprobada"
        else:
            return "Aprobada"
    
    # ============================================================
    #                    DATOS PRINCIPALES
    # ============================================================
    
    def get_ordenes_compra(self, fecha_inicio: str, fecha_fin: str,
                           status_filter: str = None,
                           receive_filter: str = None,
                           search_text: str = None) -> List[Dict]:
        """
        Obtiene las órdenes de compra con estados calculados.
        Optimizado: Trae datos en batches y procesa en memoria.
        """
        # Dominio base
        domain = [
            ['state', 'in', ['draft', 'to approve', 'purchase']],
            ['date_order', '>=', fecha_inicio],
            ['date_order', '<=', fecha_fin + ' 23:59:59']
        ]
        
        if search_text:
            domain.append(['name', 'ilike', search_text])
        
        # === Batch 1: POs básicas ===
        pos = self.odoo.search_read(
            'purchase.order',
            domain,
            ['id', 'name', 'partner_id', 'company_id', 'amount_total', 
             'state', 'date_order', 'message_ids', 'activity_ids'],
            limit=500,
            order='date_order desc'
        )
        
        if not pos:
            return []
        
        po_ids = [po['id'] for po in pos]
        
        # === Batch 2: Estado de recepción (en paralelo conceptualmente) ===
        receive_status_map = self.compute_receive_status(po_ids)
        
        # === Batch 3: Mensajes y actividades (para aprobaciones) ===
        msg_ids_all = set()
        act_ids_all = set()
        
        for po in pos:
            msg_ids_all.update(po.get('message_ids', []))
            act_ids_all.update(po.get('activity_ids', []))
        
        # Leer mensajes (para detectar aprobaciones)
        messages_by_po = {}
        if msg_ids_all:
            try:
                msgs = self.odoo.search_read(
                    'mail.message',
                    [['id', 'in', list(msg_ids_all)]],
                    ['id', 'res_id', 'author_id', 'body'],
                    limit=2000
                )
                for m in msgs:
                    po_id = m.get('res_id')
                    if po_id:
                        messages_by_po.setdefault(po_id, []).append(m)
            except Exception:
                pass
        
        # Leer actividades (para pendientes)
        activities_by_po = {}
        user_ids = set()
        if act_ids_all:
            try:
                acts = self.odoo.search_read(
                    'mail.activity',
                    [['id', 'in', list(act_ids_all)]],
                    ['id', 'res_id', 'user_id', 'state'],
                    limit=1000
                )
                for a in acts:
                    po_id = a.get('res_id')
                    if po_id:
                        activities_by_po.setdefault(po_id, []).append(a)
                    if a.get('user_id'):
                        uid = a['user_id'][0] if isinstance(a['user_id'], (list, tuple)) else a['user_id']
                        user_ids.add(uid)
            except Exception:
                pass
        
        # Leer usuarios para nombres
        users = {}
        if user_ids:
            try:
                for u in self.odoo.read('res.users', list(user_ids), ['id', 'name']):
                    users[u['id']] = u['name']
            except Exception:
                pass
        
        # === Procesar cada PO ===
        result = []
        
        for po in pos:
            po_id = po['id']
            po_name = po['name']
            po_state = po.get('state', '')
            po_amount = float(po.get('amount_total') or 0)
            po_date = po.get('date_order') or ''
            
            partner_name = po.get('partner_id', [None, ''])
            if isinstance(partner_name, (list, tuple)):
                partner_name = partner_name[1] if len(partner_name) > 1 else ''
            
            company_name = po.get('company_id', [None, ''])
            if isinstance(company_name, (list, tuple)):
                company_name = company_name[1] if len(company_name) > 1 else ''
            
            # Detectar aprobados por mensajes
            approved_set = set()
            for m in messages_by_po.get(po_id, []):
                body = (m.get('body') or '').replace('&nbsp;', ' ').lower()
                if 'aprob' in body:
                    author = m.get('author_id')
                    if author:
                        uname = author[1] if isinstance(author, (list, tuple)) else str(author)
                        if uname:
                            approved_set.add(uname)
            
            # Detectar pendientes por actividades
            pending_set = set()
            for a in activities_by_po.get(po_id, []):
                if a.get('state') == 'done':
                    continue
                user = a.get('user_id')
                if user:
                    uid = user[0] if isinstance(user, (list, tuple)) else user
                    uname = users.get(uid, '')
                    if uname:
                        pending_set.add(uname)
            
            pending_set -= approved_set
            
            # Calcular estados
            required_count = len(approved_set | pending_set) or None
            approval_status = self.compute_approval_status(
                po_state, len(approved_set), required_count
            )
            receive_status = receive_status_map.get(po_id, "No se recepciona")
            
            # Aplicar filtros
            if status_filter and status_filter != "Todos":
                if approval_status != status_filter:
                    continue
            
            if receive_filter and receive_filter != "Todos":
                if receive_status != receive_filter:
                    continue
            
            # Formatear fecha
            fecha_str = str(po_date)[:10] if po_date else ''
            
            result.append({
                'po_id': po_id,
                'name': po_name,
                'date_order': fecha_str,
                'partner': partner_name,
                'company': company_name,
                'amount_total': round(po_amount, 0),
                'po_state': po_state,
                'approval_status': approval_status,
                'receive_status': receive_status,
                'approved_by': ', '.join(sorted(approved_set)),
                'pending_users': ', '.join(sorted(pending_set)),
            })
        
        return result
    
    def get_overview(self, fecha_inicio: str, fecha_fin: str) -> Dict:
        """
        KPIs consolidados de compras.
        """
        # Usar caché para overview
        cache_key = self._get_cache_key('overview', fecha_inicio, fecha_fin)
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        # Obtener todas las POs sin filtros
        ordenes = self.get_ordenes_compra(fecha_inicio, fecha_fin)
        
        total_pos = len(ordenes)
        monto_total = sum(o['amount_total'] for o in ordenes)
        
        # Contar por estado aprobación
        en_revision = sum(1 for o in ordenes if o['approval_status'] == 'En revisión')
        parcial_aprobada = sum(1 for o in ordenes if o['approval_status'] == 'Parcialmente aprobada')
        aprobadas = sum(1 for o in ordenes if o['approval_status'] == 'Aprobada')
        rechazadas = sum(1 for o in ordenes if o['approval_status'] == 'Rechazada')
        
        # Contar por estado recepción
        no_recepcionada = sum(1 for o in ordenes if o['receive_status'] == 'No recepcionada')
        recepcion_parcial = sum(1 for o in ordenes if o['receive_status'] == 'Recepción parcial')
        recepcionada = sum(1 for o in ordenes if o['receive_status'] == 'Recepcionada totalmente')
        no_aplica = sum(1 for o in ordenes if o['receive_status'] == 'No se recepciona')
        
        # Montos por estado
        monto_aprobado = sum(o['amount_total'] for o in ordenes if o['approval_status'] == 'Aprobada')
        monto_pendiente = sum(o['amount_total'] for o in ordenes if o['approval_status'] in ('En revisión', 'Parcialmente aprobada'))
        
        result = {
            'total_pos': total_pos,
            'monto_total': round(monto_total, 0),
            'monto_aprobado': round(monto_aprobado, 0),
            'monto_pendiente': round(monto_pendiente, 0),
            'en_revision': en_revision,
            'parcial_aprobada': parcial_aprobada,
            'aprobadas': aprobadas,
            'rechazadas': rechazadas,
            'no_recepcionada': no_recepcionada,
            'recepcion_parcial': recepcion_parcial,
            'recepcionada': recepcionada,
            'no_aplica_recepcion': no_aplica,
            'pct_aprobadas': round(aprobadas / total_pos * 100, 1) if total_pos > 0 else 0,
            'pct_recepcionadas': round(recepcionada / (total_pos - no_aplica) * 100, 1) if (total_pos - no_aplica) > 0 else 0
        }
        
        self._set_cached(cache_key, result)
        return result
    
    # ============================================================
    #                    LÍNEAS DE CRÉDITO
    # ============================================================
    
    def get_lineas_credito(self) -> List[Dict]:
        """
        Obtiene proveedores con línea de crédito activa y calcula uso.
        
        Lógica:
        - Línea Total = x_studio_linea_credito_monto
        - Usado = Suma de facturas pendientes de pago (account.move con amount_residual > 0)
        - Disponible = Línea Total - Usado
        """
        # Buscar partners con línea de crédito activa
        partners = self.odoo.search_read(
            'res.partner',
            [['x_studio_linea_credito_activa', '=', True]],
            ['id', 'name', 'x_studio_linea_credito_monto', 'currency_id'],
            limit=200
        )
        
        if not partners:
            return []
        
        partner_ids = [p['id'] for p in partners]
        
        # Buscar facturas pendientes de pago (amount_residual > 0)
        # Facturas de proveedor: move_type = 'in_invoice'
        facturas = self.odoo.search_read(
            'account.move',
            [
                ['partner_id', 'in', partner_ids],
                ['move_type', '=', 'in_invoice'],
                ['state', '=', 'posted'],
                ['amount_residual', '>', 0]
            ],
            ['id', 'name', 'partner_id', 'amount_total', 'amount_residual', 
             'invoice_date', 'invoice_date_due', 'invoice_origin'],
            limit=1000,
            order='invoice_date_due asc'
        )
        
        # Agrupar facturas por partner
        facturas_by_partner = {}
        for f in facturas:
            partner_info = f.get('partner_id')
            pid = partner_info[0] if isinstance(partner_info, (list, tuple)) else partner_info
            if pid:
                facturas_by_partner.setdefault(pid, []).append(f)
        
        result = []
        
        for p in partners:
            partner_id = p['id']
            partner_name = p['name']
            linea_total = float(p.get('x_studio_linea_credito_monto') or 0)
            
            # Calcular monto usado (facturas pendientes)
            facturas_partner = facturas_by_partner.get(partner_id, [])
            monto_usado = sum(float(f.get('amount_residual') or 0) for f in facturas_partner)
            
            # Calcular disponible
            disponible = linea_total - monto_usado
            pct_uso = (monto_usado / linea_total * 100) if linea_total > 0 else 0
            
            # Preparar detalle de facturas
            facturas_detalle = []
            for f in facturas_partner:
                fecha_venc = f.get('invoice_date_due') or ''
                if fecha_venc:
                    fecha_venc = str(fecha_venc)[:10]
                
                facturas_detalle.append({
                    'factura_id': f['id'],
                    'numero': f.get('name', ''),
                    'monto_total': round(float(f.get('amount_total') or 0), 0),
                    'monto_pendiente': round(float(f.get('amount_residual') or 0), 0),
                    'fecha': str(f.get('invoice_date') or '')[:10],
                    'fecha_vencimiento': fecha_venc,
                    'origen': f.get('invoice_origin') or ''
                })
            
            # Determinar estado
            if disponible <= 0:
                estado = 'Sin cupo'
                alerta = '🔴'
            elif pct_uso >= 80:
                estado = 'Cupo bajo'
                alerta = '🟡'
            else:
                estado = 'Disponible'
                alerta = '🟢'
            
            result.append({
                'partner_id': partner_id,
                'partner_name': partner_name,
                'linea_total': round(linea_total, 0),
                'monto_usado': round(monto_usado, 0),
                'disponible': round(disponible, 0),
                'pct_uso': round(pct_uso, 1),
                'estado': estado,
                'alerta': alerta,
                'num_facturas': len(facturas_partner),
                'facturas': facturas_detalle
            })
        
        # Ordenar por % uso descendente (más críticos primero)
        result.sort(key=lambda x: x['pct_uso'], reverse=True)
        return result
    
    def get_lineas_credito_resumen(self) -> Dict:
        """
        Resumen de líneas de crédito para KPIs.
        """
        lineas = self.get_lineas_credito()
        
        total_linea = sum(l['linea_total'] for l in lineas)
        total_usado = sum(l['monto_usado'] for l in lineas)
        total_disponible = sum(l['disponible'] for l in lineas)
        
        sin_cupo = sum(1 for l in lineas if l['estado'] == 'Sin cupo')
        cupo_bajo = sum(1 for l in lineas if l['estado'] == 'Cupo bajo')
        disponibles = sum(1 for l in lineas if l['estado'] == 'Disponible')
        
        return {
            'total_proveedores': len(lineas),
            'total_linea': round(total_linea, 0),
            'total_usado': round(total_usado, 0),
            'total_disponible': round(total_disponible, 0),
            'pct_uso_global': round(total_usado / total_linea * 100, 1) if total_linea > 0 else 0,
            'sin_cupo': sin_cupo,
            'cupo_bajo': cupo_bajo,
            'disponibles': disponibles
        }

