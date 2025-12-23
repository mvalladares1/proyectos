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
from backend.services.currency_service import CurrencyService


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
        # Dominio base - incluir todos los estados excepto cancelado
        domain = [
            ['state', 'not in', ['cancel']],  # Excluir solo cancelados
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
             'state', 'date_order', 'message_ids', 'activity_ids', 'currency_id', 'create_uid'],
            limit=500,
            order='date_order desc'
        )
        
        if not pos:
            return []
        
        po_ids = [po['id'] for po in pos]
        
        # === Batch 2: Estado de recepción ===
        receive_status_map = self.compute_receive_status(po_ids)
        
        # === Batch 3: Líneas de producto ===
        po_lines = self.odoo.search_read(
            'purchase.order.line',
            [['order_id', 'in', po_ids]],
            ['order_id', 'product_id', 'name', 'product_qty', 'price_unit', 'price_subtotal'],
            limit=3000
        )
        
        # Crear mapa de monedas por PO
        currency_by_po = {}
        for po in pos:
            pid = po['id']
            currency_info = po.get('currency_id')
            currency_name = ''
            if isinstance(currency_info, (list, tuple)) and len(currency_info) > 1:
                currency_name = currency_info[1]
            elif isinstance(currency_info, str):
                currency_name = currency_info
            currency_by_po[pid] = 'USD' if (currency_name and 'USD' in currency_name.upper()) else 'CLP'
        
        # Obtener tipo de cambio una vez
        usd_rate = CurrencyService.get_usd_to_clp_rate()
        
        lines_by_po = {}
        for line in po_lines:
            order_info = line.get('order_id')
            oid = order_info[0] if isinstance(order_info, (list, tuple)) else order_info
            if oid:
                product_info = line.get('product_id')
                product_name = product_info[1] if isinstance(product_info, (list, tuple)) else line.get('name', '')
                
                price_unit = line.get('price_unit', 0)
                subtotal = line.get('price_subtotal', 0)
                
                # Convertir a CLP si la OC está en USD
                if currency_by_po.get(oid) == 'USD':
                    price_unit = price_unit * usd_rate
                    subtotal = subtotal * usd_rate
                
                lines_by_po.setdefault(oid, []).append({
                    'producto': (product_name or '')[:50],
                    'cantidad': line.get('product_qty', 0),
                    'price_unit': round(price_unit, 0),
                    'subtotal': round(subtotal, 0)
                })
        
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
        
        # Agregar los creadores de PO a la lista de usuarios
        for po in pos:
            creator = po.get('create_uid')
            if creator:
                creator_id = creator[0] if isinstance(creator, (list, tuple)) else creator
                if creator_id:
                    user_ids.add(creator_id)
        
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
            po_amount_original = float(po.get('amount_total') or 0)
            po_amount = po_amount_original
            po_date = po.get('date_order') or ''
            
            # Detectar moneda y convertir a CLP si es USD
            currency_info = po.get('currency_id')
            currency_name = ''
            if isinstance(currency_info, (list, tuple)) and len(currency_info) > 1:
                currency_name = currency_info[1]
            elif isinstance(currency_info, str):
                currency_name = currency_info
            
            # Si la moneda es USD, convertir a CLP
            is_usd = currency_name and 'USD' in currency_name.upper()
            exchange_rate = None
            if is_usd:
                exchange_rate = CurrencyService.get_usd_to_clp_rate()
                po_amount = CurrencyService.convert_usd_to_clp(po_amount_original)
            
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
            
            # Obtener nombre del creador
            creator = po.get('create_uid')
            creator_id = creator[0] if isinstance(creator, (list, tuple)) else creator if creator else None
            created_by = users.get(creator_id, '') if creator_id else ''
            
            result.append({
                'po_id': po_id,
                'name': po_name,
                'date_order': fecha_str,
                'partner': partner_name,
                'company': company_name,
                'amount_total': round(po_amount, 0),
                'amount_original': round(po_amount_original, 2) if is_usd else None,
                'currency_original': 'USD' if is_usd else 'CLP',
                'exchange_rate': round(exchange_rate, 2) if exchange_rate else None,
                'po_state': po_state,
                'approval_status': approval_status,
                'receive_status': receive_status,
                'approved_by': ', '.join(sorted(approved_set)),
                'pending_users': ', '.join(sorted(pending_set)),
                'created_by': created_by,
                'lineas': lines_by_po.get(po_id, [])
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
    
    def get_lineas_credito(self, fecha_desde: str = None) -> List[Dict]:
        """
        Obtiene proveedores con línea de crédito activa y calcula uso.
        
        Args:
            fecha_desde: Fecha desde la cual calcular uso (YYYY-MM-DD). Si es None, no filtra.
        
        Lógica de cálculo:
        - Línea Total = x_studio_linea_credito_monto
        - Usado = Facturas no pagadas + Recepciones reales sin facturar
        - Disponible = Línea Total - Usado
        
        Detalle:
        1. Facturas de proveedor con amount_residual > 0 (no pagadas)
        2. Recepciones reales sin facturar: stock.move en estado 'done' con
           purchase_line_id donde qty_received > qty_invoiced
        3. OCs tentativas (informativo): OCs confirmadas sin factura asociada
           (no afecta disponibilidad, solo referencia)
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
        
        # === 1. FACTURAS NO PAGADAS ===
        factura_domain = [
            ['partner_id', 'in', partner_ids],
            ['move_type', '=', 'in_invoice'],
            ['state', '=', 'posted'],
            ['amount_residual', '>', 0]
        ]
        # Filtrar por fecha si se especifica
        if fecha_desde:
            factura_domain.append(['invoice_date', '>=', fecha_desde])
        
        facturas = self.odoo.search_read(
            'account.move',
            factura_domain,
            ['id', 'name', 'partner_id', 'amount_total', 'amount_residual', 
             'invoice_date', 'invoice_date_due', 'invoice_origin', 'currency_id'],
            limit=1000,
            order='invoice_date_due asc'
        )
        
        # Agrupar facturas por partner y obtener orígenes (OCs facturadas)
        facturas_by_partner = {}
        ocs_facturadas = set()
        
        for f in facturas:
            partner_info = f.get('partner_id')
            pid = partner_info[0] if isinstance(partner_info, (list, tuple)) else partner_info
            if pid:
                facturas_by_partner.setdefault(pid, []).append(f)
            # Guardar OCs que ya tienen factura
            origen = f.get('invoice_origin') or ''
            if origen:
                for oc in origen.split(','):
                    ocs_facturadas.add(oc.strip())
        
        # === 2. OCs SIN FACTURA (USO TENTATIVO/COMPROMETIDO) ===
        # Incluir todos los estados excepto cancelado: draft, sent, to approve, purchase, done
        oc_domain = [
            ['partner_id', 'in', partner_ids],
            ['state', 'not in', ['cancel']]  # Incluir solicitudes de presupuesto también
        ]
        if fecha_desde:
            oc_domain.append(['date_order', '>=', fecha_desde])
        
        ocs = self.odoo.search_read(
            'purchase.order',
            oc_domain,
            ['id', 'name', 'partner_id', 'amount_total', 'date_order', 'invoice_ids', 'currency_id'],
            limit=1000,
            order='date_order desc'
        )
        
        if not ocs:
            ocs = []
        
        oc_ids = [oc['id'] for oc in ocs]
        oc_info_map = {oc['id']: oc for oc in ocs}
        
        # Filtrar OCs que NO tienen factura asociada (uso tentativo)
        ocs_sin_factura_by_partner = {}
        for oc in ocs:
            # Si la OC ya está en los orígenes de facturas, ignorar
            if oc['name'] in ocs_facturadas:
                continue
            # Si tiene invoice_ids, verificar si alguna está pendiente
            if oc.get('invoice_ids') and len(oc['invoice_ids']) > 0:
                continue  # Ya tiene factura asociada
            
            partner_info = oc.get('partner_id')
            pid = partner_info[0] if isinstance(partner_info, (list, tuple)) else partner_info
            if pid:
                ocs_sin_factura_by_partner.setdefault(pid, []).append(oc)
        
        # === 3. RECEPCIONES REALES SIN FACTURAR (via purchase.order.line) ===
        # Buscar líneas de OC donde qty_received > 0 (algo se recibió)
        # y calcular la diferencia con qty_invoiced (lo no facturado)
        recepciones_sin_facturar_by_partner = {}
        
        if oc_ids:
            # Leer todas las líneas de PO de estas OCs
            po_lines = self.odoo.search_read(
                'purchase.order.line',
                [['order_id', 'in', oc_ids]],
                ['id', 'order_id', 'product_id', 'name', 'product_qty', 'qty_received', 'qty_invoiced', 'price_unit'],
                limit=5000
            )
            
            # DEBUG: Log para ver qué datos vienen
            print(f"[DEBUG LINEAS CREDITO] Encontradas {len(po_lines)} líneas de OC")
            
            # Procesar cada línea y calcular el valor pendiente
            for line in po_lines:
                qty_received = float(line.get('qty_received') or 0)
                qty_invoiced = float(line.get('qty_invoiced') or 0)
                price_unit = float(line.get('price_unit') or 0)
                
                # DEBUG para ver los valores
                if qty_received > 0:
                    order_info = line.get('order_id')
                    oc_id = order_info[0] if isinstance(order_info, (list, tuple)) else order_info
                    oc_data = oc_info_map.get(oc_id, {})
                    oc_name = oc_data.get('name', 'N/A')
                    print(f"[DEBUG] Línea OC {oc_name}: qty_recv={qty_received}, qty_inv={qty_invoiced}, pendiente={qty_received - qty_invoiced}")
                
                # Solo considerar si hay recepción sin facturar
                qty_pendiente = qty_received - qty_invoiced
                if qty_pendiente <= 0:
                    continue
                
                # Calcular monto pendiente de esta línea
                monto_pendiente = qty_pendiente * price_unit
                
                # Obtener info de la OC
                order_info = line.get('order_id')
                oc_id = order_info[0] if isinstance(order_info, (list, tuple)) else order_info
                oc_data = oc_info_map.get(oc_id, {})
                
                # Obtener partner_id de la OC
                partner_info = oc_data.get('partner_id')
                pid = partner_info[0] if isinstance(partner_info, (list, tuple)) else partner_info
                
                if pid:
                    # Agregar información de esta recepción pendiente
                    if pid not in recepciones_sin_facturar_by_partner:
                        recepciones_sin_facturar_by_partner[pid] = {}
                    
                    # Agrupar por OC para el detalle
                    oc_name = oc_data.get('name', '')
                    if oc_name not in recepciones_sin_facturar_by_partner[pid]:
                        recepciones_sin_facturar_by_partner[pid][oc_name] = {
                            'oc_id': oc_id,
                            'name': oc_name,
                            'date_order': oc_data.get('date_order'),
                            'currency_id': oc_data.get('currency_id'),
                            'monto_pendiente': 0,
                            'lineas_count': 0
                        }
                    
                    recepciones_sin_facturar_by_partner[pid][oc_name]['monto_pendiente'] += monto_pendiente
                    recepciones_sin_facturar_by_partner[pid][oc_name]['lineas_count'] += 1
            
            # DEBUG: Mostrar resultados
            for pid, ocs in recepciones_sin_facturar_by_partner.items():
                for oc_name, data in ocs.items():
                    print(f"[DEBUG RESULTADO] Partner {pid}: {oc_name} = ${data['monto_pendiente']:,.0f}")
        
        # === 4. STOCK.PICKING EN TODOS LOS ESTADOS EXCEPTO BORRADOR/CANCELADO ===
        # Recepciones pendientes de facturar (incluir assigned, waiting, confirmed, done)
        recepciones_preparadas_by_partner = {}
        
        try:
            if oc_ids:
                # Buscar pickings de compra en todos los estados excepto borrador y cancelado
                pickings = self.odoo.search_read(
                    'stock.picking',
                    [
                        ['purchase_id', 'in', oc_ids],
                        ['state', 'not in', ['draft', 'cancel']],  # Incluir assigned, waiting, confirmed, done
                        ['picking_type_code', '=', 'incoming']  # Solo recepciones
                    ],
                    ['id', 'name', 'purchase_id', 'partner_id', 'scheduled_date', 'move_ids', 'state'],
                    limit=1000
                )
                
                print(f"[DEBUG PICKINGS] Encontrados {len(pickings)} pickings (estados: assigned, waiting, confirmed, done)")
                
                if pickings:
                    picking_ids = [p['id'] for p in pickings]
                    picking_info_map = {p['id']: p for p in pickings}
                
                    # Obtener move lines de estos pickings para calcular valores
                    moves = self.odoo.search_read(
                        'stock.move',
                        [['picking_id', 'in', picking_ids]],
                        ['id', 'picking_id', 'product_id', 'product_uom_qty', 'quantity_done', 'price_unit', 'purchase_line_id'],
                        limit=5000
                    )
                    
                    # Procesar cada move y calcular el valor pendiente
                    for move in moves:
                        qty_demand = float(move.get('product_uom_qty') or 0)
                        qty_done = float(move.get('quantity_done') or 0)
                        price_unit = float(move.get('price_unit') or 0)
                        
                        # Solo considerar si hay demanda sin completar
                        qty_pendiente = qty_demand - qty_done
                        if qty_pendiente <= 0:
                            continue
                        
                        # Calcular monto pendiente
                        monto_pendiente = qty_pendiente * price_unit
                        
                        # Obtener info del picking
                        picking_info = move.get('picking_id')
                        picking_id = picking_info[0] if isinstance(picking_info, (list, tuple)) else picking_info
                        picking_data = picking_info_map.get(picking_id, {})
                        
                        # Obtener partner_id del picking o de la OC
                        partner_info = picking_data.get('partner_id')
                        pid = partner_info[0] if isinstance(partner_info, (list, tuple)) else partner_info
                        
                        # Si no tiene partner, buscar en la OC
                        if not pid:
                            purchase_info = picking_data.get('purchase_id')
                            oc_id = purchase_info[0] if isinstance(purchase_info, (list, tuple)) else purchase_info
                            oc_data = oc_info_map.get(oc_id, {})
                            partner_info = oc_data.get('partner_id')
                            pid = partner_info[0] if isinstance(partner_info, (list, tuple)) else partner_info
                        
                        if pid:
                            picking_name = picking_data.get('name', '')
                            if pid not in recepciones_preparadas_by_partner:
                                recepciones_preparadas_by_partner[pid] = {}
                            
                            if picking_name not in recepciones_preparadas_by_partner[pid]:
                                purchase_info = picking_data.get('purchase_id')
                                oc_id = purchase_info[0] if isinstance(purchase_info, (list, tuple)) else purchase_info
                                oc_data = oc_info_map.get(oc_id, {})
                                
                                recepciones_preparadas_by_partner[pid][picking_name] = {
                                    'picking_id': picking_id,
                                    'name': picking_name,
                                    'oc_id': oc_id,
                                    'oc_name': oc_data.get('name', ''),
                                    'date': picking_data.get('scheduled_date'),
                                    'currency_id': oc_data.get('currency_id'),
                                    'monto_pendiente': 0,
                                    'lineas_count': 0
                                }
                            
                            recepciones_preparadas_by_partner[pid][picking_name]['monto_pendiente'] += monto_pendiente
                            recepciones_preparadas_by_partner[pid][picking_name]['lineas_count'] += 1
                    
                    # DEBUG
                    for pid, pickings_dict in recepciones_preparadas_by_partner.items():
                        for pick_name, data in pickings_dict.items():
                            print(f"[DEBUG PREPARADO] Partner {pid}: {pick_name} = ${data['monto_pendiente']:,.0f}")
        except Exception as e:
            print(f"[ERROR PICKINGS] Error al obtener pickings preparados: {e}")
            # Continuar sin pickings preparados, no bloquear la carga

        
        # === PROCESAR CADA PARTNER ===
        result = []
        
        for p in partners:
            partner_id = p['id']
            partner_name = p['name']
            linea_total = float(p.get('x_studio_linea_credito_monto') or 0)
            
            # Detectar moneda del partner (para la línea de crédito)
            partner_currency = p.get('currency_id')
            partner_currency_name = ''
            if isinstance(partner_currency, (list, tuple)) and len(partner_currency) > 1:
                partner_currency_name = partner_currency[1]
            elif isinstance(partner_currency, str):
                partner_currency_name = partner_currency
            
            # Convertir línea total a CLP si está en USD
            if partner_currency_name and 'USD' in partner_currency_name.upper():
                linea_total = CurrencyService.convert_usd_to_clp(linea_total)
            
            # Facturas no pagadas (con conversión de moneda)
            facturas_partner = facturas_by_partner.get(partner_id, [])
            monto_facturas = 0.0
            for f in facturas_partner:
                f_amount = float(f.get('amount_residual') or 0)
                # Detectar moneda de la factura
                f_currency = f.get('currency_id')
                f_currency_name = ''
                if isinstance(f_currency, (list, tuple)) and len(f_currency) > 1:
                    f_currency_name = f_currency[1]
                elif isinstance(f_currency, str):
                    f_currency_name = f_currency
                # Convertir si está en USD
                if f_currency_name and 'USD' in f_currency_name.upper():
                    f_amount = CurrencyService.convert_usd_to_clp(f_amount)
                monto_facturas += f_amount
            
            # OCs sin factura - USO TENTATIVO/COMPROMETIDO (con conversión de moneda)
            ocs_partner = ocs_sin_factura_by_partner.get(partner_id, [])
            monto_ocs_tentativo = 0.0
            num_ocs_tentativas = 0
            for oc in ocs_partner:
                oc_amount = float(oc.get('amount_total') or 0)
                oc_currency = oc.get('currency_id')
                oc_currency_name = ''
                if isinstance(oc_currency, (list, tuple)) and len(oc_currency) > 1:
                    oc_currency_name = oc_currency[1]
                elif isinstance(oc_currency, str):
                    oc_currency_name = oc_currency
                if oc_currency_name and 'USD' in oc_currency_name.upper():
                    oc_amount = CurrencyService.convert_usd_to_clp(oc_amount)
                monto_ocs_tentativo += oc_amount
                num_ocs_tentativas += 1
            
            # Recepciones sin facturar - USO REAL (con conversión de moneda)
            recepciones_partner = recepciones_sin_facturar_by_partner.get(partner_id, {})
            monto_recepciones = 0.0
            num_recepciones = 0
            for oc_name, oc_data in recepciones_partner.items():
                oc_amount = float(oc_data.get('monto_pendiente') or 0)
                # Detectar moneda de la OC
                oc_currency = oc_data.get('currency_id')
                oc_currency_name = ''
                if isinstance(oc_currency, (list, tuple)) and len(oc_currency) > 1:
                    oc_currency_name = oc_currency[1]
                elif isinstance(oc_currency, str):
                    oc_currency_name = oc_currency
                # Convertir si está en USD
                if oc_currency_name and 'USD' in oc_currency_name.upper():
                    oc_amount = CurrencyService.convert_usd_to_clp(oc_amount)
                monto_recepciones += oc_amount
                num_recepciones += 1
            
            # Recepciones PREPARADAS - también afectan la línea (con conversión de moneda)
            preparadas_partner = recepciones_preparadas_by_partner.get(partner_id, {})
            monto_preparadas = 0.0
            num_preparadas = 0
            for pick_name, pick_data in preparadas_partner.items():
                pick_amount = float(pick_data.get('monto_pendiente') or 0)
                # Detectar moneda de la OC
                pick_currency = pick_data.get('currency_id')
                pick_currency_name = ''
                if isinstance(pick_currency, (list, tuple)) and len(pick_currency) > 1:
                    pick_currency_name = pick_currency[1]
                elif isinstance(pick_currency, str):
                    pick_currency_name = pick_currency
                # Convertir si está en USD
                if pick_currency_name and 'USD' in pick_currency_name.upper():
                    pick_amount = CurrencyService.convert_usd_to_clp(pick_amount)
                monto_preparadas += pick_amount
                num_preparadas += 1
            
            # Total usado = Facturas + Recepciones reales + Recepciones preparadas
            monto_usado = monto_facturas + monto_recepciones + monto_preparadas
            
            # Calcular disponible basado en uso real
            disponible = linea_total - monto_usado
            pct_uso = (monto_usado / linea_total * 100) if linea_total > 0 else 0
            
            # Preparar detalle de facturas
            detalle_facturas = []
            exchange_rate = CurrencyService.get_usd_to_clp_rate()  # Obtener una vez para todos
            for f in facturas_partner:
                fecha_venc = f.get('invoice_date_due') or ''
                if fecha_venc:
                    fecha_venc = str(fecha_venc)[:10]
                
                # Monto con conversión de moneda
                f_monto_original = float(f.get('amount_residual') or 0)
                f_monto = f_monto_original
                f_currency = f.get('currency_id')
                f_currency_name = ''
                if isinstance(f_currency, (list, tuple)) and len(f_currency) > 1:
                    f_currency_name = f_currency[1]
                elif isinstance(f_currency, str):
                    f_currency_name = f_currency
                f_is_usd = f_currency_name and 'USD' in f_currency_name.upper()
                if f_is_usd:
                    f_monto = CurrencyService.convert_usd_to_clp(f_monto_original)
                
                detalle_facturas.append({
                    'tipo': 'Factura',
                    'numero': f.get('name', ''),
                    'monto': round(f_monto, 0),
                    'monto_original': round(f_monto_original, 2) if f_is_usd else None,
                    'moneda_original': 'USD' if f_is_usd else 'CLP',
                    'tipo_cambio': round(exchange_rate, 2) if f_is_usd else None,
                    'fecha': str(f.get('invoice_date') or '')[:10],
                    'fecha_vencimiento': fecha_venc,
                    'origen': f.get('invoice_origin') or '',
                    'estado': 'Pendiente pago'
                })
            
            # Preparar detalle de recepciones sin facturar (REALES)
            for oc_name, oc_data in recepciones_partner.items():
                # Monto con conversión de moneda
                oc_monto_original = float(oc_data.get('monto_pendiente') or 0)
                oc_monto = oc_monto_original
                oc_currency = oc_data.get('currency_id')
                oc_currency_name = ''
                if isinstance(oc_currency, (list, tuple)) and len(oc_currency) > 1:
                    oc_currency_name = oc_currency[1]
                elif isinstance(oc_currency, str):
                    oc_currency_name = oc_currency
                oc_is_usd = oc_currency_name and 'USD' in oc_currency_name.upper()
                if oc_is_usd:
                    oc_monto = CurrencyService.convert_usd_to_clp(oc_monto_original)
                
                detalle_facturas.append({
                    'tipo': 'Recepción',
                    'numero': oc_data.get('name', ''),
                    'oc_id': oc_data.get('oc_id'),  # Para enlace Odoo
                    'monto': round(oc_monto, 0),
                    'monto_original': round(oc_monto_original, 2) if oc_is_usd else None,
                    'moneda_original': 'USD' if oc_is_usd else 'CLP',
                    'tipo_cambio': round(exchange_rate, 2) if oc_is_usd else None,
                    'fecha': str(oc_data.get('date_order') or '')[:10],
                    'fecha_vencimiento': '',
                    'origen': '',
                    'estado': 'Recepcionado sin facturar'
                })
            
            # Preparar detalle de recepciones PREPARADAS (afectan línea)
            for pick_name, pick_data in preparadas_partner.items():
                pick_monto_original = float(pick_data.get('monto_pendiente') or 0)
                pick_monto = pick_monto_original
                pick_currency = pick_data.get('currency_id')
                pick_currency_name = ''
                if isinstance(pick_currency, (list, tuple)) and len(pick_currency) > 1:
                    pick_currency_name = pick_currency[1]
                elif isinstance(pick_currency, str):
                    pick_currency_name = pick_currency
                pick_is_usd = pick_currency_name and 'USD' in pick_currency_name.upper()
                if pick_is_usd:
                    pick_monto = CurrencyService.convert_usd_to_clp(pick_monto_original)
                
                detalle_facturas.append({
                    'tipo': 'Recep. Preparada',
                    'numero': pick_data.get('name', ''),
                    'picking_id': pick_data.get('picking_id'),  # Para enlace Odoo
                    'oc_id': pick_data.get('oc_id'),  # Para enlace Odoo  
                    'oc_name': pick_data.get('oc_name', ''),
                    'monto': round(pick_monto, 0),
                    'monto_original': round(pick_monto_original, 2) if pick_is_usd else None,
                    'moneda_original': 'USD' if pick_is_usd else 'CLP',
                    'tipo_cambio': round(exchange_rate, 2) if pick_is_usd else None,
                    'fecha': str(pick_data.get('date') or '')[:10],
                    'fecha_vencimiento': '',
                    'origen': pick_data.get('oc_name', ''),
                    'estado': 'Preparado (pendiente recepción)'
                })
            
            # Preparar detalle de OCs sin factura (TENTATIVAS) - solo informativo
            # Excluir OCs que ya tienen recepciones preparadas para evitar duplicados
            ocs_con_picking_preparado = set()
            for pick_name, pick_data in preparadas_partner.items():
                if pick_data.get('oc_id'):
                    ocs_con_picking_preparado.add(pick_data['oc_id'])
            
            for oc in ocs_partner:
                # Si esta OC ya tiene picking preparado, saltar
                if oc.get('id') in ocs_con_picking_preparado:
                    continue
                oc_monto_original = float(oc.get('amount_total') or 0)
                oc_monto = oc_monto_original
                oc_currency = oc.get('currency_id')
                oc_currency_name = ''
                if isinstance(oc_currency, (list, tuple)) and len(oc_currency) > 1:
                    oc_currency_name = oc_currency[1]
                elif isinstance(oc_currency, str):
                    oc_currency_name = oc_currency
                oc_is_usd = oc_currency_name and 'USD' in oc_currency_name.upper()
                if oc_is_usd:
                    oc_monto = CurrencyService.convert_usd_to_clp(oc_monto_original)
                
                detalle_facturas.append({
                    'tipo': 'OC Tentativa',
                    'numero': oc.get('name', ''),
                    'oc_id': oc.get('id'),  # Para enlace Odoo
                    'monto': round(oc_monto, 0),
                    'monto_original': round(oc_monto_original, 2) if oc_is_usd else None,
                    'moneda_original': 'USD' if oc_is_usd else 'CLP',
                    'tipo_cambio': round(exchange_rate, 2) if oc_is_usd else None,
                    'fecha': str(oc.get('date_order') or '')[:10],
                    'fecha_vencimiento': '',
                    'origen': '',
                    'estado': 'Sin facturar (tentativo)'
                })
            
            # Ordenar por monto descendente
            detalle_facturas.sort(key=lambda x: x['monto'], reverse=True)
            
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
                'monto_facturas': round(monto_facturas, 0),
                'monto_ocs': round(monto_ocs_tentativo, 0),  # OCs sin factura (tentativo)
                'monto_recepciones': round(monto_recepciones, 0),  # Recepciones completadas sin facturar
                'monto_preparadas': round(monto_preparadas, 0),  # Recepciones en estado PREPARADO
                'disponible': round(disponible, 0),
                'pct_uso': round(pct_uso, 1),
                'estado': estado,
                'alerta': alerta,
                'num_facturas': len(facturas_partner),
                'num_ocs': num_ocs_tentativas,
                'num_recepciones': num_recepciones,
                'num_preparadas': num_preparadas,
                'detalle': detalle_facturas
            })
        
        # Ordenar por % uso descendente (más críticos primero)
        result.sort(key=lambda x: x['pct_uso'], reverse=True)
        return result
    
    def get_lineas_credito_resumen(self, fecha_desde: str = None) -> Dict:
        """
        Resumen de líneas de crédito para KPIs.
        """
        lineas = self.get_lineas_credito(fecha_desde=fecha_desde)
        
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
    
    def get_orden_lineas(self, po_id: int) -> List[Dict]:
        """
        Obtiene las líneas de producto de una orden de compra específica.
        """
        lines = self.odoo.search_read(
            'purchase.order.line',
            [['order_id', '=', po_id]],
            ['product_id', 'name', 'product_qty', 'qty_received', 'price_unit', 'price_subtotal'],
            limit=100
        )
        
        result = []
        for line in lines:
            product_info = line.get('product_id')
            product_name = product_info[1] if isinstance(product_info, (list, tuple)) else line.get('name', '')
            
            result.append({
                'producto': product_name[:50],
                'cantidad': line.get('product_qty', 0),
                'recibido': line.get('qty_received', 0),
                'price_unit': round(line.get('price_unit', 0), 0),
                'subtotal': round(line.get('price_subtotal', 0), 0)
            })
        
        return result

