"""
DEBUG: Investigar recepciones problemáticas
- RF/RFP/IN/00507 (cancelada, no debería aparecer)
- RF/RFP/IN/01045 (tiene devolución RF/OUT/02586 que no se refleja)
"""
import xmlrpc.client
from datetime import datetime

# Configuración
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

# Conectar
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

print("=" * 100)
print("INVESTIGACIÓN DE RECEPCIONES PROBLEMÁTICAS")
print("=" * 100)

# ==================================================================================
# PROBLEMA 1: RF/RFP/IN/00507 - Recepción cancelada que aparece en el dashboard
# ==================================================================================
print("\n" + "=" * 100)
print("PROBLEMA 1: RF/RFP/IN/00507 (Recepción cancelada)")
print("=" * 100)

pickings_507 = models.execute_kw(db, uid, password,
    'stock.picking', 'search_read',
    [[['name', '=', 'RF/RFP/IN/00507']]],
    {'fields': ['id', 'name', 'state', 'scheduled_date', 'partner_id', 
                'picking_type_id', 'origin', 'x_studio_categora_de_producto',
                'x_studio_gua_de_despacho']}
)

if pickings_507:
    p507 = pickings_507[0]
    print(f"\n✅ ENCONTRADO:")
    print(f"   ID: {p507['id']}")
    print(f"   Nombre: {p507['name']}")
    print(f"   ESTADO: {p507['state']} ⚠️")
    print(f"   Fecha: {p507.get('scheduled_date', 'N/A')}")
    print(f"   Productor: {p507.get('partner_id', 'N/A')}")
    print(f"   Picking Type: {p507.get('picking_type_id', 'N/A')}")
    print(f"   Categoría: {p507.get('x_studio_categora_de_producto', 'N/A')}")
    print(f"   Guía Despacho: {p507.get('x_studio_gua_de_despacho', 'N/A')}")
    print(f"   Origin (OC): {p507.get('origin', 'N/A')}")
    
    # Obtener movimientos asociados
    print(f"\n📦 Movimientos de stock:")
    moves_507 = models.execute_kw(db, uid, password,
        'stock.move', 'search_read',
        [[['picking_id', '=', p507['id']]]],
        {'fields': ['id', 'product_id', 'quantity_done', 'product_uom_qty', 
                    'state', 'price_unit', 'product_uom']}
    )
    
    if moves_507:
        for m in moves_507:
            print(f"   - Producto: {m.get('product_id', 'N/A')}")
            print(f"     Cantidad planificada: {m.get('product_uom_qty', 0)}")
            print(f"     Cantidad hecha: {m.get('quantity_done', 0)}")
            print(f"     Estado: {m.get('state', 'N/A')}")
            print(f"     Precio unitario: {m.get('price_unit', 0)}")
    else:
        print("   ❌ No tiene movimientos")
    
    print(f"\n🔍 ANÁLISIS:")
    if p507['state'] == 'cancel':
        print(f"   ✅ El picking ESTÁ cancelado en Odoo")
        print(f"   ⚠️  PERO aparece en el dashboard de recepciones")
        print(f"   💡 SOLUCIÓN: Filtrar pickings con state='cancel' en recepcion_service.py")
    elif p507['state'] == 'done':
        print(f"   ⚠️  El picking está en estado 'done' (completado)")
        print(f"   ❓ Verificar si debería estar cancelado o si hay error en los datos")
    else:
        print(f"   ⚠️  Estado inesperado: {p507['state']}")
        
else:
    print("\n❌ NO SE ENCONTRÓ RF/RFP/IN/00507")

# ==================================================================================
# PROBLEMA 2: RF/RFP/IN/01045 - Recepción con devolución que no se refleja
# ==================================================================================
print("\n" + "=" * 100)
print("PROBLEMA 2: RF/RFP/IN/01045 (Recepción con devolución RF/OUT/02586)")
print("=" * 100)

pickings_1045 = models.execute_kw(db, uid, password,
    'stock.picking', 'search_read',
    [[['name', '=', 'RF/RFP/IN/01045']]],
    {'fields': ['id', 'name', 'state', 'scheduled_date', 'partner_id', 
                'picking_type_id', 'origin', 'x_studio_categora_de_producto',
                'x_studio_gua_de_despacho']}
)

if pickings_1045:
    p1045 = pickings_1045[0]
    print(f"\n✅ RECEPCIÓN ORIGINAL (RF/RFP/IN/01045):")
    print(f"   ID: {p1045['id']}")
    print(f"   Estado: {p1045['state']}")
    print(f"   Fecha: {p1045.get('scheduled_date', 'N/A')}")
    print(f"   Productor: {p1045.get('partner_id', 'N/A')}")
    print(f"   Guía: {p1045.get('x_studio_gua_de_despacho', 'N/A')}")
    
    # Obtener movimientos de la recepción
    print(f"\n📦 Movimientos de stock (RECEPCIÓN):")
    moves_1045 = models.execute_kw(db, uid, password,
        'stock.move', 'search_read',
        [[['picking_id', '=', p1045['id']]]],
        {'fields': ['id', 'product_id', 'quantity_done', 'product_uom_qty', 
                    'state', 'price_unit', 'product_uom']}
    )
    
    total_recepcion = 0
    if moves_1045:
        for m in moves_1045:
            qty = m.get('quantity_done', 0)
            uom = m.get('product_uom', ['N/A', 'kg'])
            uom_name = uom[1] if isinstance(uom, list) else 'kg'
            
            # Solo sumar al total si es en kg, no unidades
            if uom_name.lower() == 'kg':
                total_recepcion += qty
            
            print(f"   - Producto: {m.get('product_id', 'N/A')}")
            print(f"     Cantidad hecha: {qty} {uom_name}")
            print(f"     Precio: ${m.get('price_unit', 0):,.2f}")
    
    print(f"\n   📊 TOTAL RECEPCIÓN (solo kg): {total_recepcion:.2f} kg")
    
    # Buscar devolución asociada
    print(f"\n" + "=" * 80)
    print(f"🔍 BUSCANDO DEVOLUCIÓN RF/OUT/02586:")
    print("=" * 80)
    
    devoluciones = models.execute_kw(db, uid, password,
        'stock.picking', 'search_read',
        [[['name', '=', 'RF/OUT/02586']]],
        {'fields': ['id', 'name', 'state', 'scheduled_date', 'partner_id', 
                    'picking_type_id', 'origin', 'x_studio_categora_de_producto']}
    )
    
    if devoluciones:
        dev = devoluciones[0]
        print(f"\n✅ DEVOLUCIÓN ENCONTRADA:")
        print(f"   ID: {dev['id']}")
        print(f"   Nombre: {dev['name']}")
        print(f"   Estado: {dev['state']}")
        print(f"   Fecha: {dev.get('scheduled_date', 'N/A')}")
        print(f"   Origin: {dev.get('origin', 'N/A')}")
        print(f"   Picking Type: {dev.get('picking_type_id', 'N/A')}")
        
        # Obtener movimientos de la devolución
        print(f"\n📦 Movimientos de stock (DEVOLUCIÓN):")
        moves_dev = models.execute_kw(db, uid, password,
            'stock.move', 'search_read',
            [[['picking_id', '=', dev['id']]]],
            {'fields': ['id', 'product_id', 'quantity_done', 'product_uom_qty', 
                        'state', 'price_unit', 'product_uom']}
        )
        
        total_devolucion = 0
        if moves_dev:
            for m in moves_dev:
                qty = m.get('quantity_done', 0)
                uom = m.get('product_uom', ['N/A', 'kg'])
                uom_name = uom[1] if isinstance(uom, list) else 'kg'
                
                # Solo sumar al total si es en kg, no unidades
                if uom_name.lower() == 'kg':
                    total_devolucion += qty
                
                print(f"   - Producto: {m.get('product_id', 'N/A')}")
                print(f"     Cantidad devuelta: {qty} {uom_name}")
                print(f"     Precio: ${m.get('price_unit', 0):,.2f}")
        
        print(f"\n   📊 TOTAL DEVOLUCIÓN (solo kg): {total_devolucion:.2f} kg")
        
        print(f"\n" + "=" * 80)
        print(f"📊 RESUMEN:")
        print("=" * 80)
        print(f"   Kg Recibidos (IN/01045):   {total_recepcion:.2f} kg")
        print(f"   Kg Devueltos (OUT/02586):  {total_devolucion:.2f} kg")
        print(f"   NETO ESPERADO:             {total_recepcion - total_devolucion:.2f} kg")
        print(f"\n   📌 El dashboard debería mostrar: {total_recepcion - total_devolucion:.2f} kg")
        print(f"   ⚠️  Verificar qué muestra actualmente el dashboard")
        
        print(f"\n🔍 ANÁLISIS:")
        print(f"   El campo 'origin' de la devolución es: '{dev.get('origin', 'N/A')}'")
        if dev.get('origin') == 'RF/RFP/IN/01045':
            print(f"   ✅ La devolución está correctamente vinculada a la recepción")
            print(f"   💡 SOLUCIÓN: Restar devoluciones en recepcion_service.py usando campo 'origin'")
        else:
            print(f"   ⚠️  La vinculación puede no estar clara")
            print(f"   💡 Investigar otros campos de vinculación")
        
    else:
        print("\n❌ NO SE ENCONTRÓ la devolución RF/OUT/02586")
        print("   💡 Verificar el nombre exacto de la devolución")
        
        # Buscar devoluciones relacionadas por fecha/productor
        print(f"\n🔍 Buscando devoluciones del mismo productor en fechas cercanas...")
        partner_id = p1045['partner_id'][0] if isinstance(p1045['partner_id'], list) else p1045['partner_id']
        
        devoluciones_periodo = models.execute_kw(db, uid, password,
            'stock.picking', 'search_read',
            [[['partner_id', '=', partner_id],
              ['scheduled_date', '>=', '2025-12-31'],
              ['scheduled_date', '<=', '2026-01-05'],
              ['picking_type_id', 'in', [2, 3, 5]]]],  # IDs de devoluciones/salidas
            {'fields': ['id', 'name', 'state', 'scheduled_date', 'origin', 'picking_type_id']}
        )
        
        if devoluciones_periodo:
            print(f"\n   Devoluciones encontradas:")
            for d in devoluciones_periodo:
                print(f"      {d['name']} - Fecha: {d.get('scheduled_date', 'N/A')} - Origin: {d.get('origin', 'N/A')}")
        else:
            print(f"   No se encontraron devoluciones en ese período")
            
else:
    print("\n❌ NO SE ENCONTRÓ RF/RFP/IN/01045")

# ==================================================================================
# INVESTIGAR PICKING TYPES
# ==================================================================================
print("\n" + "=" * 100)
print("📋 PICKING TYPES (para entender IDs)")
print("=" * 100)

picking_types = models.execute_kw(db, uid, password,
    'stock.picking.type', 'search_read',
    [[]],
    {'fields': ['id', 'name', 'code', 'sequence_code'], 'limit': 50}
)

print("\nPICKING TYPES relevantes:")
for pt in picking_types:
    if pt['code'] in ['incoming', 'outgoing', 'internal']:
        print(f"   ID {pt['id']:3} - {pt['name']:40} - Code: {pt['code']:10} - Seq: {pt.get('sequence_code', 'N/A')}")

print("\n" + "=" * 100)
print("FIN DEL DIAGNÓSTICO")
print("=" * 100)
