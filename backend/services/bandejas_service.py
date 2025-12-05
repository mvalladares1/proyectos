"""
Servicio de Bandejas - Lógica de negocio para movimientos y stock de bandejas
Migrado desde el dashboard original de bandejas
"""
from typing import Optional, Dict, List, Any
from datetime import datetime
import pandas as pd

from shared.odoo_client import OdooClient
from shared.constants import CATEGORIAS


class BandejasService:
    """
    Servicio para manejar datos de bandejas desde Odoo.
    Incluye movimientos de entrada/salida y niveles de stock.
    """
    
    # ID de categoría de bandejas en Odoo
    CATEG_ID = CATEGORIAS['bandejas_productor']  # 107
    
    def __init__(self, username: str = None, password: str = None):
        self.odoo = OdooClient(username=username, password=password)
    
    def _get_product_ids(self) -> List[int]:
        """Obtiene los IDs de productos de la categoría bandejas."""
        return self.odoo.search('product.product', [['categ_id', '=', self.CATEG_ID]])
    
    def get_movimientos_entrada(self, fecha_desde: Optional[str] = None) -> pd.DataFrame:
        """
        Obtiene los movimientos de entrada de bandejas (recepción de productores).
        Basado en stock.move con filtros específicos.
        """
        product_ids = self._get_product_ids()
        if not product_ids:
            return pd.DataFrame()
        
        domain = [
            ['product_id', 'in', product_ids],
            ['state', 'in', ['done', 'assigned']]
        ]
        
        if fecha_desde:
            domain.append(['date', '>=', fecha_desde])
        
        # Buscar movimientos
        move_ids = self.odoo.search('stock.move', domain, limit=20000, order='date desc')
        moves = self.odoo.read('stock.move', move_ids, 
                              ['date', 'picking_id', 'product_id', 'product_uom_qty', 'quantity_done', 'state'])
        
        if not moves:
            return pd.DataFrame()
        
        # Obtener detalles de pickings y productos
        picking_ids = list(set([m['picking_id'][0] for m in moves if m.get('picking_id')]))
        product_ids_in_moves = list(set([m['product_id'][0] for m in moves if m.get('product_id')]))
        
        # Mapear pickings
        picking_map = {}
        if picking_ids:
            pickings = self.odoo.read('stock.picking', picking_ids, ['origin', 'partner_id'])
            for p in pickings:
                p_data = {'origin': p['origin'] or '', 'partner_name': 'Unknown'}
                if p.get('partner_id'):
                    p_data['partner_name'] = p['partner_id'][1]
                picking_map[p['id']] = p_data
        
        # Mapear códigos de producto
        product_code_map = {}
        if product_ids_in_moves:
            products = self.odoo.read('product.product', product_ids_in_moves, ['default_code'])
            for p in products:
                product_code_map[p['id']] = p.get('default_code', '')
        
        # Procesar movimientos
        final_moves = []
        for move in moves:
            picking_id = move['picking_id'][0] if move.get('picking_id') else None
            p_data = picking_map.get(picking_id, {'origin': '', 'partner_name': 'Unknown'})
            origin = p_data['origin']
            
            # Filtrar por origen válido (P = Purchase, OC = Order)
            is_valid = origin.startswith('P') or origin.startswith('OC')
            if not is_valid:
                if move['date'] < '2025-01-01' and origin.startswith('Retorno'):
                    is_valid = True
            
            if not is_valid:
                continue
            
            qty = move['quantity_done']
            if qty == 0 and move['state'] == 'done':
                qty = move['product_uom_qty']
            
            if qty > 0:
                final_moves.append({
                    'date_order': move['date'],
                    'product_name': move['product_id'][1] if move.get('product_id') else '',
                    'default_code': product_code_map.get(move['product_id'][0], '') if move.get('product_id') else '',
                    'order_name': origin,
                    'partner_name': p_data['partner_name'],
                    'qty_received': qty
                })
        
        return pd.DataFrame(final_moves)
    
    def get_movimientos_salida(self, fecha_desde: Optional[str] = None) -> pd.DataFrame:
        """
        Obtiene los movimientos de salida de bandejas (despacho a productores).
        Filtrado por picking_type_id = 2 (RF/OUT - Expediciones).
        """
        product_ids = self._get_product_ids()
        if not product_ids:
            return pd.DataFrame()
        
        domain = [
            ['picking_type_id', '=', 2],  # Expediciones
            ['product_id', 'in', product_ids],
            ['state', 'in', ['done', 'assigned']]
        ]
        
        if fecha_desde:
            domain.append(['date', '>=', fecha_desde])
        
        move_ids = self.odoo.search('stock.move', domain, limit=20000, order='date desc')
        moves = self.odoo.read('stock.move', move_ids,
                              ['date', 'picking_id', 'product_id', 'product_uom_qty', 'quantity_done', 'state'])
        
        if not moves:
            return pd.DataFrame()
        
        # Obtener detalles
        picking_ids = list(set([m['picking_id'][0] for m in moves if m.get('picking_id')]))
        product_ids_in_moves = list(set([m['product_id'][0] for m in moves if m.get('product_id')]))
        
        picking_map = {}
        if picking_ids:
            pickings = self.odoo.read('stock.picking', picking_ids, ['partner_id', 'name'])
            for p in pickings:
                p_name = p['partner_id'][1] if p.get('partner_id') else 'Unknown'
                picking_map[p['id']] = {'partner_name': p_name, 'picking_name': p['name']}
        
        product_code_map = {}
        if product_ids_in_moves:
            products = self.odoo.read('product.product', product_ids_in_moves, ['default_code'])
            for p in products:
                product_code_map[p['id']] = p.get('default_code', '')
        
        final_moves = []
        for move in moves:
            picking_id = move['picking_id'][0] if move.get('picking_id') else None
            p_data = picking_map.get(picking_id, {'partner_name': 'Unknown', 'picking_name': ''})
            
            qty = move['quantity_done']
            if qty == 0 and move['state'] == 'done':
                qty = move['product_uom_qty']
            
            if qty > 0:
                final_moves.append({
                    'date': move['date'],
                    'product_name': move['product_id'][1] if move.get('product_id') else '',
                    'default_code': product_code_map.get(move['product_id'][0], '') if move.get('product_id') else '',
                    'picking_name': p_data['picking_name'],
                    'partner_name': p_data['partner_name'],
                    'state': move['state'],
                    'qty_sent': qty
                })
        
        return pd.DataFrame(final_moves)
    
    def get_stock(self) -> pd.DataFrame:
        """
        Obtiene el stock actual de bandejas (Limpias vs Sucias).
        Basado en stock.quant con location.usage = 'internal'.
        """
        product_ids = self._get_product_ids()
        if not product_ids:
            return pd.DataFrame()
        
        domain = [
            ['product_id', 'in', product_ids],
            ['location_id.usage', '=', 'internal']
        ]
        
        quant_ids = self.odoo.search('stock.quant', domain)
        quants = self.odoo.read('stock.quant', quant_ids, ['product_id', 'quantity', 'location_id'])
        
        # Agregar por producto
        product_qty_map = {}
        for q in quants:
            pid = q['product_id'][0]
            product_qty_map[pid] = product_qty_map.get(pid, 0) + q['quantity']
        
        # Obtener detalles de productos
        products = self.odoo.read('product.product', product_ids, ['display_name', 'default_code'])
        
        data = []
        for p in products:
            pid = p['id']
            code = str(p.get('default_code', '')).strip().upper()
            
            # Clasificar por código (L = Limpia)
            tipo = 'Limpia' if code.endswith('L') else 'Sucia'
            
            data.append({
                'display_name': p['display_name'],
                'default_code': p.get('default_code', ''),
                'qty_available': product_qty_map.get(pid, 0),
                'tipo': tipo
            })
        
        return pd.DataFrame(data)
    
    def get_resumen_por_productor(self, anio: Optional[int] = None, mes: Optional[int] = None) -> pd.DataFrame:
        """
        Obtiene el resumen de bandejas por productor.
        """
        df_in = self.get_movimientos_entrada()
        df_out = self.get_movimientos_salida()
        
        # Filtrar por fecha si se especifica
        if not df_in.empty:
            df_in['date_order'] = pd.to_datetime(df_in['date_order'])
            if anio:
                df_in = df_in[df_in['date_order'].dt.year == anio]
            if mes:
                df_in = df_in[df_in['date_order'].dt.month == mes]
        
        if not df_out.empty:
            df_out['date'] = pd.to_datetime(df_out['date'])
            if anio:
                df_out = df_out[df_out['date'].dt.year == anio]
            if mes:
                df_out = df_out[df_out['date'].dt.month == mes]
        
        # Agrupar por productor
        df_in_grouped = pd.DataFrame(columns=['partner_name', 'recepcionadas'])
        df_out_grouped = pd.DataFrame(columns=['partner_name', 'despachadas'])
        
        if not df_in.empty:
            df_in_grouped = df_in.groupby('partner_name')['qty_received'].sum().reset_index()
            df_in_grouped.columns = ['partner_name', 'recepcionadas']
        
        if not df_out.empty:
            df_out_done = df_out[df_out['state'] == 'done']
            if not df_out_done.empty:
                df_out_grouped = df_out_done.groupby('partner_name')['qty_sent'].sum().reset_index()
                df_out_grouped.columns = ['partner_name', 'despachadas']
        
        # Merge
        df_merged = pd.merge(df_in_grouped, df_out_grouped, on='partner_name', how='outer').fillna(0)
        df_merged['en_productor'] = df_merged['despachadas'] - df_merged['recepcionadas']
        
        return df_merged
