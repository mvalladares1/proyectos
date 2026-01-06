"""
Módulo compartido para Bandejas.
Contiene funciones de utilidad, formateo y carga de datos desde Odoo.
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from shared.odoo_client import OdooClient


# --------------------- Funciones de formateo ---------------------

def fmt_fecha(fecha_str):
    """Convierte fecha ISO a formato DD/MM/AAAA."""
    if not fecha_str:
        return ""
    try:
        if isinstance(fecha_str, (pd.Timestamp, datetime)):
            return fecha_str.strftime("%d/%m/%Y")
        if isinstance(fecha_str, str):
            if " " in fecha_str:
                fecha_str = fecha_str.split(" ")[0]
            elif "T" in fecha_str:
                fecha_str = fecha_str.split("T")[0]
            dt = datetime.strptime(fecha_str, "%Y-%m-%d")
            return dt.strftime("%d/%m/%Y")
    except:
        pass
    return str(fecha_str)


def fmt_numero(valor, decimales=0):
    """Formatea número con punto como miles y coma como decimal (chileno)."""
    if valor is None:
        return "0"
    try:
        if decimales > 0:
            formatted = f"{valor:,.{decimales}f}"
        else:
            formatted = f"{valor:,.0f}"
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return formatted
    except:
        return str(valor)


# --------------------- Funciones de carga de datos ---------------------

@st.cache_data(ttl=300)
def load_in_data(_username, _password):
    """Carga movimientos de entrada de bandejas."""
    client = OdooClient(username=_username, password=_password)
    return get_tray_in_movements(client)


@st.cache_data(ttl=300)
def load_out_data(_username, _password):
    """Carga movimientos de salida de bandejas."""
    client = OdooClient(username=_username, password=_password)
    return get_tray_out_movements(client)


@st.cache_data(ttl=300)
def load_stock_data(_username, _password):
    """Carga stock actual de bandejas."""
    client = OdooClient(username=_username, password=_password)
    return get_tray_stock_levels(client)


def get_tray_in_movements(client):
    """Movimientos de entrada de bandejas (recepción de productores)."""
    CATEG_ID = 107  # BANDEJAS A PRODUCTOR
    
    product_ids = client.search('product.product', [['categ_id', '=', CATEG_ID]])
    if not product_ids:
        return pd.DataFrame()
    
    domain = [
        ['product_id', 'in', product_ids],
        ['state', 'in', ['done', 'assigned']]
    ]
    
    move_ids = client.search('stock.move', domain, limit=20000, order='date desc')
    moves = client.read('stock.move', move_ids, 
                       ['date', 'picking_id', 'product_id', 'product_uom_qty', 'quantity_done', 'state'])
    
    if not moves:
        return pd.DataFrame()
    
    picking_ids = list(set([m['picking_id'][0] for m in moves if m.get('picking_id')]))
    product_ids_in_moves = list(set([m['product_id'][0] for m in moves if m.get('product_id')]))
    
    picking_map = {}
    if picking_ids:
        pickings = client.read('stock.picking', picking_ids, ['origin', 'partner_id'])
        for p in pickings:
            p_data = {'origin': p['origin'] or '', 'partner_name': 'Unknown'}
            if p.get('partner_id'):
                p_data['partner_name'] = p['partner_id'][1]
            picking_map[p['id']] = p_data
    
    product_code_map = {}
    if product_ids_in_moves:
        products = client.read('product.product', product_ids_in_moves, ['default_code'])
        for p in products:
            product_code_map[p['id']] = p.get('default_code', '')
    
    final_moves = []
    for move in moves:
        picking_id = move['picking_id'][0] if move.get('picking_id') else None
        p_data = picking_map.get(picking_id, {'origin': '', 'partner_name': 'Unknown'})
        origin = p_data['origin']
        
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


def get_tray_out_movements(client):
    """Movimientos de salida de bandejas (despacho a productores)."""
    CATEG_ID = 107
    
    product_ids = client.search('product.product', [['categ_id', '=', CATEG_ID]])
    if not product_ids:
        return pd.DataFrame()
    
    domain = [
        ['picking_type_id', '=', 2],  # Expediciones
        ['product_id', 'in', product_ids],
        ['state', 'in', ['done', 'assigned']]
    ]
    
    move_ids = client.search('stock.move', domain, limit=20000, order='date desc')
    moves = client.read('stock.move', move_ids,
                       ['date', 'picking_id', 'product_id', 'product_uom_qty', 'quantity_done', 'state'])
    
    if not moves:
        return pd.DataFrame()
    
    picking_ids = list(set([m['picking_id'][0] for m in moves if m.get('picking_id')]))
    product_ids_in_moves = list(set([m['product_id'][0] for m in moves if m.get('product_id')]))
    
    picking_map = {}
    if picking_ids:
        pickings = client.read('stock.picking', picking_ids, ['partner_id', 'name'])
        for p in pickings:
            p_name = p['partner_id'][1] if p.get('partner_id') else 'Unknown'
            picking_map[p['id']] = {'partner_name': p_name, 'picking_name': p['name']}
    
    product_code_map = {}
    if product_ids_in_moves:
        products = client.read('product.product', product_ids_in_moves, ['default_code'])
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


def get_tray_stock_levels(client):
    """Stock actual de bandejas."""
    CATEG_ID = 107
    
    product_ids = client.search('product.product', [['categ_id', '=', CATEG_ID]])
    if not product_ids:
        return pd.DataFrame()
    
    domain = [
        ['product_id', 'in', product_ids],
        ['location_id.usage', '=', 'internal']
    ]
    
    quant_ids = client.search('stock.quant', domain)
    quants = client.read('stock.quant', quant_ids, ['product_id', 'quantity', 'location_id'])
    
    product_qty_map = {}
    for q in quants:
        pid = q['product_id'][0]
        product_qty_map[pid] = product_qty_map.get(pid, 0) + q['quantity']
    
    products = client.read('product.product', product_ids, ['display_name', 'default_code'])
    
    data = []
    for p in products:
        pid = p['id']
        data.append({
            'display_name': p['display_name'],
            'default_code': p.get('default_code', ''),
            'qty_available': product_qty_map.get(pid, 0)
        })
    
    return pd.DataFrame(data)


# --------------------- Inicialización de Session State ---------------------

def init_session_state():
    """Inicializa variables de session_state para el módulo Bandejas."""
    defaults = {
        'bandejas_df_in': None,
        'bandejas_df_out': None,
        'bandejas_df_stock': None,
        'bandejas_data_loaded': False,
        'bandejas_loading': False,
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default
