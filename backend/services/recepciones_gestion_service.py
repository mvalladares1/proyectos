"""
Servicio de Gestión de Recepciones MP
Estados de validación, control de calidad y usuarios pendientes.
Similar a ComprasService pero para stock.picking de recepciones.
"""
from typing import List, Dict, Optional
from datetime import datetime
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


class RecepcionesGestionService:
    """Servicio para gestión de recepciones de MP con estados de validación y QC."""
    
    # Caché en memoria
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
    #                    ESTADOS DE VALIDACIÓN
    # ============================================================
    
    def compute_validation_status(self, picking_state: str) -> str:
        """
        Calcula el estado de validación del picking.
        
        Estados Odoo:
        - draft: Borrador
        - waiting: Esperando otra operación
        - confirmed: Confirmado (esperando disponibilidad)
        - assigned: Asignado (listo para validar)
        - done: Hecho/Validado
        - cancel: Cancelado
        """
        status_map = {
            'done': 'Validada',
            'assigned': 'Lista para validar',
            'confirmed': 'Confirmada',
            'waiting': 'En espera',
            'draft': 'Borrador',
            'cancel': 'Cancelada'
        }
        return status_map.get(picking_state, 'Desconocido')
    
    def compute_qc_status(self, has_qc: bool, qc_todo: bool, qc_fail: bool, 
                          calific_final: str = None, qc_state: str = None) -> str:
        """
        Calcula el estado del control de calidad.
        
        Returns:
            - 'Con QC Aprobado': Tiene QC y está completo/aprobado
            - 'Con QC Pendiente': Tiene QC pero está pendiente
            - 'QC Fallido': El QC falló
            - 'Sin QC': No tiene control de calidad asociado
            
        Lógica mejorada:
            1. Si qc_state == 'pass' → Con QC Aprobado
            2. Si tiene calific_final numérica → Con QC Aprobado (QC completado)
            3. Si qc_state == 'fail' → QC Fallido
            4. Si qc_fail=True → QC Fallido
            5. Si qc_todo=True → Con QC Pendiente
            6. Si qc_todo=False y qc_fail=False → Con QC Aprobado
        """
        if not has_qc:
            return 'Sin QC'
        
        # Prioridad 1: Estado explícito 'pass' del quality.check
        if qc_state == 'pass':
            return 'Con QC Aprobado'
        
        # Prioridad 2: Si tiene calificación final numérica, el QC fue completado
        if calific_final:
            calific_str = str(calific_final).strip()
            # Si es un número (ej: "85.60", "88.00"), el QC está aprobado
            try:
                float(calific_str)
                return 'Con QC Aprobado'
            except (ValueError, TypeError):
                pass
        
        # Prioridad 3: Estados de fallo
        if qc_state == 'fail' or qc_fail:
            return 'QC Fallido'
        
        # Prioridad 4: QC pendiente
        if qc_todo:
            return 'Con QC Pendiente'
        
        # Por defecto, si qc_todo=False y qc_fail=False, considerarlo aprobado
        return 'Con QC Aprobado'
    
    # ============================================================
    #                    DATOS PRINCIPALES
    # ============================================================
    
    def get_recepciones_gestion(self, fecha_inicio: str, fecha_fin: str,
                                 status_filter: str = None,
                                 qc_filter: str = None,
                                 search_text: str = None) -> List[Dict]:
        """
        Obtiene las recepciones de MP con estados de validación y QC.
        Similar a get_ordenes_compra en ComprasService.
        """
        # Dominio base para recepciones de MP
        domain = [
            ['picking_type_id', '=', 1],  # Recepciones
            ['x_studio_categora_de_producto', '=', 'MP'],
            ['scheduled_date', '>=', fecha_inicio],
            ['scheduled_date', '<=', fecha_fin + ' 23:59:59']
        ]
        
        if search_text:
            domain.append(['name', 'ilike', search_text])
        
        # === Batch 1: Pickings básicos ===
        pickings = self.odoo.search_read(
            'stock.picking',
            domain,
            ['id', 'name', 'partner_id', 'scheduled_date', 'state',
             'check_ids', 'quality_check_todo', 'quality_check_fail',
             'activity_ids', 'message_ids', 'x_studio_gua_de_despacho',
             'x_studio_tiene_calidad', 'x_studio_fecha_de_qc'],
            limit=5000,
            order='scheduled_date desc'
        )
        
        if not pickings:
            return []
        
        picking_ids = [p['id'] for p in pickings]
        
        # === Batch 2: Obtener quality.check para más detalle ===
        all_check_ids = set()
        for p in pickings:
            all_check_ids.update(p.get('check_ids', []) or [])
        
        qc_map = {}
        if all_check_ids:
            try:
                checks = self.odoo.search_read(
                    'quality.check',
                    [['id', 'in', list(all_check_ids)]],
                    ['id', 'picking_id', 'x_studio_tipo_de_fruta', 
                     'x_studio_calific_final', 'x_studio_jefe_de_calidad_y_aseguramiento_',
                     'quality_state', 'state'],  # Agregar quality_state y state (none/pass/fail)
                    limit=1000
                )
                for c in checks:
                    picking = c.get('picking_id')
                    if picking:
                        pk_id = picking[0] if isinstance(picking, (list, tuple)) else picking
                        qc_map[pk_id] = c
            except Exception:
                pass
        
        # === Batch 3: Actividades pendientes ===
        all_activity_ids = set()
        for p in pickings:
            all_activity_ids.update(p.get('activity_ids', []) or [])
        
        activities_by_picking = {}
        user_ids = set()
        if all_activity_ids:
            try:
                activities = self.odoo.search_read(
                    'mail.activity',
                    [['id', 'in', list(all_activity_ids)]],
                    ['id', 'res_id', 'user_id', 'state', 'activity_type_id', 'summary'],
                    limit=1000
                )
                for a in activities:
                    picking_id = a.get('res_id')
                    if picking_id:
                        activities_by_picking.setdefault(picking_id, []).append(a)
                    if a.get('user_id'):
                        uid = a['user_id'][0] if isinstance(a['user_id'], (list, tuple)) else a['user_id']
                        user_ids.add(uid)
            except Exception:
                pass
        
        # === Batch 4: Mensajes para detectar validaciones ===
        all_message_ids = set()
        for p in pickings:
            msgs = p.get('message_ids', []) or []
            # Solo los últimos 20 mensajes por picking
            all_message_ids.update(msgs[:20] if len(msgs) > 20 else msgs)
        
        messages_by_picking = {}
        if all_message_ids:
            try:
                messages = self.odoo.search_read(
                    'mail.message',
                    [['id', 'in', list(all_message_ids)]],
                    ['id', 'res_id', 'author_id', 'body', 'subtype_id'],
                    limit=2000
                )
                for m in messages:
                    picking_id = m.get('res_id')
                    if picking_id:
                        messages_by_picking.setdefault(picking_id, []).append(m)
            except Exception:
                pass
        
        # === Batch 5: Usuarios para nombres ===
        users = {}
        if user_ids:
            try:
                for u in self.odoo.read('res.users', list(user_ids), ['id', 'name']):
                    users[u['id']] = u['name']
            except Exception:
                pass
        
        # === Procesar cada picking ===
        result = []
        
        for p in pickings:
            picking_id = p['id']
            picking_name = p['name']
            picking_state = p.get('state', '')
            
            # Info del proveedor/productor
            partner = p.get('partner_id')
            partner_name = partner[1] if isinstance(partner, (list, tuple)) and len(partner) > 1 else ''
            
            # Fecha
            fecha = p.get('scheduled_date') or ''
            fecha_str = str(fecha)[:10] if fecha else ''
            
            # QC Info
            check_ids = p.get('check_ids', []) or []
            has_qc = len(check_ids) > 0
            qc_todo = p.get('quality_check_todo', False) or False
            qc_fail = p.get('quality_check_fail', False) or False
            
            # Obtener calificación final del QC
            qc_info = qc_map.get(picking_id, {})
            calific_final = qc_info.get('x_studio_calific_final', '') or ''
            tipo_fruta = qc_info.get('x_studio_tipo_de_fruta', '') or ''
            jefe_calidad = qc_info.get('x_studio_jefe_de_calidad_y_aseguramiento_', '') or ''
            # Buscar el estado del QC en ambos campos posibles
            qc_state = qc_info.get('quality_state') or qc_info.get('state') or ''
            
            # Calcular estados
            validation_status = self.compute_validation_status(picking_state)
            qc_status = self.compute_qc_status(has_qc, qc_todo, qc_fail, calific_final, qc_state)
            
            # Usuarios pendientes (de actividades)
            pending_users = set()
            for a in activities_by_picking.get(picking_id, []):
                user = a.get('user_id')
                if user:
                    uid = user[0] if isinstance(user, (list, tuple)) else user
                    uname = users.get(uid, '')
                    if uname:
                        pending_users.add(uname)
            
            # Detectar quién validó (de mensajes)
            validated_by = set()
            for m in messages_by_picking.get(picking_id, []):
                body = (m.get('body') or '').lower()
                # Detectar mensajes de validación
                if any(word in body for word in ['validado', 'validada', 'done', 'hecho', 'transferencia']):
                    author = m.get('author_id')
                    if author:
                        aname = author[1] if isinstance(author, (list, tuple)) else str(author)
                        if aname:
                            validated_by.add(aname)
            
            # Aplicar filtros
            if status_filter and status_filter != "Todos":
                if validation_status != status_filter:
                    continue
            
            if qc_filter and qc_filter != "Todos":
                if qc_status != qc_filter:
                    continue
            
            result.append({
                'picking_id': picking_id,
                'name': picking_name,
                'date': fecha_str,
                'partner': partner_name,
                'guia_despacho': p.get('x_studio_gua_de_despacho', '') or '',
                'state': picking_state,
                'validation_status': validation_status,
                'qc_status': qc_status,
                'has_qc': has_qc,
                'tipo_fruta': tipo_fruta,
                'calific_final': calific_final,
                'jefe_calidad': jefe_calidad,
                'fecha_qc': str(p.get('x_studio_fecha_de_qc', '') or '')[:10],
                'pending_users': ', '.join(sorted(pending_users)),
                'validated_by': ', '.join(sorted(validated_by))
            })
        
        return result
    
    def get_overview(self, fecha_inicio: str, fecha_fin: str) -> Dict:
        """
        KPIs consolidados de gestión de recepciones.
        """
        # Usar caché
        cache_key = self._get_cache_key('recepciones_overview', fecha_inicio, fecha_fin)
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        # Obtener todas las recepciones sin filtros
        recepciones = self.get_recepciones_gestion(fecha_inicio, fecha_fin)
        
        total = len(recepciones)
        
        # Por estado de validación
        validadas = sum(1 for r in recepciones if r['validation_status'] == 'Validada')
        listas_validar = sum(1 for r in recepciones if r['validation_status'] == 'Lista para validar')
        confirmadas = sum(1 for r in recepciones if r['validation_status'] == 'Confirmada')
        en_espera = sum(1 for r in recepciones if r['validation_status'] == 'En espera')
        borrador = sum(1 for r in recepciones if r['validation_status'] == 'Borrador')
        canceladas = sum(1 for r in recepciones if r['validation_status'] == 'Cancelada')
        
        # Por estado de QC
        con_qc_aprobado = sum(1 for r in recepciones if r['qc_status'] == 'Con QC Aprobado')
        con_qc_pendiente = sum(1 for r in recepciones if r['qc_status'] == 'Con QC Pendiente')
        qc_fallido = sum(1 for r in recepciones if r['qc_status'] == 'QC Fallido')
        sin_qc = sum(1 for r in recepciones if r['qc_status'] == 'Sin QC')
        
        # Con pendientes de aprobar
        con_pendientes = sum(1 for r in recepciones if r['pending_users'])
        
        result = {
            'total_recepciones': total,
            'validadas': validadas,
            'listas_validar': listas_validar,
            'confirmadas': confirmadas,
            'en_espera': en_espera,
            'borrador': borrador,
            'canceladas': canceladas,
            'pct_validadas': round(validadas / total * 100, 1) if total > 0 else 0,
            'con_qc_aprobado': con_qc_aprobado,
            'con_qc_pendiente': con_qc_pendiente,
            'qc_fallido': qc_fallido,
            'sin_qc': sin_qc,
            'pct_con_qc': round((con_qc_aprobado + con_qc_pendiente) / total * 100, 1) if total > 0 else 0,
            'con_pendientes': con_pendientes
        }
        
        self._set_cached(cache_key, result)
        return result
