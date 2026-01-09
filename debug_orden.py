#!/usr/bin/env python3
"""
Script de debug para analizar orden RF/MO/CongTE1/00130
"""
import sys
import os
sys.path.insert(0, '/app')
from backend.services.tuneles_service import TunelesService
from shared.odoo_client import OdooClient
import json

# Conectar a Odoo con credenciales
USUARIO = os.getenv("ODOO_USER", "mvalladares@riofuturo.cl")
API_KEY = os.getenv("ODOO_API_KEY", "c0766224bec30cac071ffe43a858c9ccbd521ddd")

odoo = OdooClient(username=USUARIO, password=API_KEY)
service = TunelesService(odoo)

# Buscar la orden
ORDEN_NAME = 'RF/MO/CongTE1/00130'
print(f"{'='*80}")
print(f"ANÁLISIS DE ORDEN: {ORDEN_NAME}")
print(f"{'='*80}\n")

ordenes = odoo.search_read(
    'mrp.production',
    [('name', '=', ORDEN_NAME)],
    ['id', 'name', 'x_studio_pending_receptions', 'move_raw_ids', 'state']
)

if not ordenes:
    print(f"❌ Orden {ORDEN_NAME} NO encontrada")
    sys.exit(1)

mo = ordenes[0]
mo_id = mo['id']
mo_name = mo['name']
mo_state = mo['state']

print(f"✅ Orden encontrada")
print(f"   ID: {mo_id}")
print(f"   Estado: {mo_state}")
print(f"   Move raw IDs: {mo['move_raw_ids']}")

# Analizar JSON de pendientes
print(f"\n{'─'*80}")
print("📋 ANÁLISIS DEL JSON DE PENDIENTES")
print(f"{'─'*80}")

pending_json = mo.get('x_studio_pending_receptions')
if not pending_json:
    print("❌ No tiene campo x_studio_pending_receptions")
    sys.exit(1)

pending_data = json.loads(pending_json) if isinstance(pending_json, str) else pending_json
print(f"✅ JSON parseado correctamente")
print(f"   Pending flag: {pending_data.get('pending')}")
print(f"   Picking IDs: {pending_data.get('picking_ids', [])}")

pallets_json = pending_data.get('pallets', [])
print(f"   Total pallets en JSON: {len(pallets_json)}")

# Mostrar detalle de pallets del JSON
print(f"\n{'─'*80}")
print("📦 PALLETS EN JSON")
print(f"{'─'*80}")
for i, p in enumerate(pallets_json, 1):
    print(f"\n{i}. {p.get('codigo', 'SIN CÓDIGO')}")
    print(f"   Kg: {p.get('kg', 0)}")
    print(f"   Producto ID: {p.get('producto_id')}")
    print(f"   Picking ID: {p.get('picking_id')}")
    print(f"   Estado guardado: {p.get('estado_ultima_revision', 'NO TIENE')}")
    print(f"   Timestamp: {p.get('timestamp_ultima_revision', 'NO TIENE')}")

# Analizar stock.move.line existentes
print(f"\n{'─'*80}")
print("🔍 STOCK.MOVE.LINE ASOCIADOS A LA ORDEN")
print(f"{'─'*80}")

move_raw_ids = mo.get('move_raw_ids', [])
if not move_raw_ids:
    print("❌ No tiene move_raw_ids")
else:
    print(f"✅ Move raw IDs: {move_raw_ids}")
    
    # Buscar todos los move.line (con y sin qty_done)
    all_lines = odoo.search_read(
        'stock.move.line',
        [('move_id', 'in', move_raw_ids)],
        ['id', 'package_id', 'qty_done', 'reserved_uom_qty', 'product_id', 'state', 'lot_id']
    )
    
    print(f"\nTotal stock.move.line encontrados: {len(all_lines)}")
    
    for line in all_lines:
        pkg_name = line.get('package_id')[1] if line.get('package_id') else 'SIN PACKAGE'
        print(f"\n  Line ID: {line['id']}")
        print(f"    Package: {pkg_name}")
        print(f"    Qty done: {line.get('qty_done', 0)}")
        print(f"    Reserved: {line.get('reserved_uom_qty', 0)}")
        print(f"    State: {line.get('state')}")
        print(f"    Product: {line.get('product_id')}")
        print(f"    Lot: {line.get('lot_id')}")

# Verificar stock disponible de cada pallet
print(f"\n{'─'*80}")
print("📊 VERIFICACIÓN DE STOCK DISPONIBLE")
print(f"{'─'*80}")

for i, p in enumerate(pallets_json, 1):
    codigo = p.get('codigo', 'SIN CÓDIGO')
    print(f"\n{i}. Verificando pallet: {codigo}")
    
    # Buscar quant
    quants = odoo.search_read(
        'stock.quant',
        [
            ('package_id.name', '=', codigo),
            ('quantity', '>', 0),
            ('location_id.usage', '=', 'internal')
        ],
        ['quantity', 'location_id', 'product_id', 'lot_id', 'package_id']
    )
    
    if quants:
        print(f"   ✅ TIENE STOCK DISPONIBLE")
        for q in quants:
            print(f"      Cantidad: {q['quantity']}")
            print(f"      Location: {q.get('location_id')}")
            print(f"      Product: {q.get('product_id')}")
            print(f"      Lot: {q.get('lot_id')}")
    else:
        print(f"   ❌ NO tiene stock disponible")
        
        # Buscar en cualquier ubicación
        all_quants = odoo.search_read(
            'stock.quant',
            [('package_id.name', '=', codigo)],
            ['quantity', 'location_id', 'product_id']
        )
        if all_quants:
            print(f"   ⚠️  Encontrado en otras ubicaciones:")
            for q in all_quants:
                print(f"      Qty: {q['quantity']} - Location: {q.get('location_id')}")
        else:
            print(f"   ⚠️  No existe en ningún quant")

# Ejecutar el método obtener_detalle_pendientes
print(f"\n{'─'*80}")
print("🎯 RESULTADO DEL MÉTODO obtener_detalle_pendientes()")
print(f"{'─'*80}")

try:
    detalle = service.obtener_detalle_pendientes(mo_id)
    
    print(f"\nEstadísticas:")
    print(f"  Agregados: {detalle.get('agregados', 0)}")
    print(f"  Disponibles: {detalle.get('disponibles', 0)}")
    print(f"  Pendientes: {detalle.get('pendientes', 0)}")
    print(f"  Hay cambios nuevos: {detalle.get('hay_cambios_nuevos', False)}")
    print(f"  Nuevos disponibles: {detalle.get('nuevos_disponibles', 0)}")
    
    pallets_detalle = detalle.get('pallets', [])
    print(f"\nDetalle por pallet:")
    for p in pallets_detalle:
        print(f"\n  {p['codigo']}:")
        print(f"    Estado actual: {p['estado']} ({p['estado_label']})")
        print(f"    Estado anterior: {p.get('estado_anterior', 'N/A')}")
        print(f"    Cambio detectado: {p.get('cambio_detectado', False)}")
        print(f"    Nuevo disponible: {p.get('nuevo_disponible', False)}")
        print(f"    Tiene stock: {p.get('tiene_stock', False)}")
        print(f"    Ya agregado: {p.get('ya_agregado', False)}")
        
except Exception as e:
    print(f"❌ Error al ejecutar obtener_detalle_pendientes: {e}")
    import traceback
    traceback.print_exc()

print(f"\n{'='*80}")
print("FIN DEL ANÁLISIS")
print(f"{'='*80}")
