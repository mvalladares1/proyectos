"""
Debug script para verificar extracción de fabricaciones
Uso: python scripts/debug_fabricaciones.py

Este script ayuda a diagnosticar problemas con:
1. Detección de planta VILKUN vs RIO FUTURO
2. Extracción de componentes y subproductos
3. Filtros de especie/manejo
"""
import sys
import os

# Añadir path del proyecto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient
from datetime import datetime, timedelta

# Credenciales
USERNAME = "mvalladares@riofuturo.cl"
API_KEY = "c0766224bec30cac071ffe43a858c9ccbd521ddd"


def debug_filtro_planta():
    """Verifica detección de planta VILKUN vs RIO FUTURO."""
    print("\n" + "="*60)
    print("🏭 DEBUG: DETECCIÓN DE PLANTA")
    print("="*60)
    
    client = OdooClient(username=USERNAME, password=API_KEY)
    
    # 1. MOs con VLK en el nombre
    mos_vlk_name = client.search_read(
        'mrp.production',
        [['name', 'ilike', 'VLK'], ['state', '=', 'done']],
        ['id', 'name', 'x_studio_sala_de_proceso'],
        limit=10
    )
    
    print(f"\n📋 MOs con 'VLK' en NOMBRE: {len(mos_vlk_name)}")
    for mo in mos_vlk_name[:5]:
        print(f"  ✓ {mo['name']} | Sala: {mo.get('x_studio_sala_de_proceso', 'N/A')}")
    
    # 2. MOs con Vilkun en la sala
    mos_vilkun_sala = client.search_read(
        'mrp.production',
        [['x_studio_sala_de_proceso', 'ilike', 'vilkun'], ['state', '=', 'done']],
        ['id', 'name', 'x_studio_sala_de_proceso'],
        limit=10
    )
    
    print(f"\n📋 MOs con 'Vilkun' en SALA: {len(mos_vilkun_sala)}")
    for mo in mos_vilkun_sala[:5]:
        print(f"  ✓ {mo['name']} | Sala: {mo.get('x_studio_sala_de_proceso', 'N/A')}")
    
    # 3. MOs con VLK en la sala
    mos_vlk_sala = client.search_read(
        'mrp.production',
        [['x_studio_sala_de_proceso', 'ilike', 'VLK'], ['state', '=', 'done']],
        ['id', 'name', 'x_studio_sala_de_proceso'],
        limit=10
    )
    
    print(f"\n📋 MOs con 'VLK' en SALA: {len(mos_vlk_sala)}")
    for mo in mos_vlk_sala[:5]:
        print(f"  ✓ {mo['name']} | Sala: {mo.get('x_studio_sala_de_proceso', 'N/A')}")
    
    # 4. Salas únicas que contienen VLK o Vilkun
    all_salas = client.search_read(
        'mrp.production',
        [['state', '=', 'done']],
        ['x_studio_sala_de_proceso'],
        limit=500
    )
    
    salas_set = set()
    for mo in all_salas:
        sala = mo.get('x_studio_sala_de_proceso') or ''
        if 'vlk' in sala.lower() or 'vilkun' in sala.lower():
            salas_set.add(sala)
    
    print(f"\n📋 SALAS ÚNICAS con VLK/Vilkun: {len(salas_set)}")
    for sala in sorted(salas_set):
        print(f"  • {sala}")
    
    return mos_vlk_name, mos_vilkun_sala, mos_vlk_sala


def debug_componentes_subproductos():
    """Verifica extracción de componentes y subproductos."""
    print("\n" + "="*60)
    print("📦 DEBUG: COMPONENTES Y SUBPRODUCTOS")
    print("="*60)
    
    client = OdooClient(username=USERNAME, password=API_KEY)
    
    # Tomar una MO reciente
    mos = client.search_read(
        'mrp.production',
        [['state', '=', 'done']],
        ['id', 'name', 'x_studio_sala_de_proceso', 'move_raw_ids', 'move_finished_ids', 'product_id'],
        limit=5,
        order='date_planned_start desc'
    )
    
    if not mos:
        print("❌ No se encontraron MOs")
        return
    
    for mo in mos[:2]:
        print(f"\n{'─'*50}")
        print(f"📄 MO: {mo['name']}")
        print(f"   Sala: {mo.get('x_studio_sala_de_proceso', 'N/A')}")
        print(f"   Producto: {mo.get('product_id', [0, 'N/A'])[1] if mo.get('product_id') else 'N/A'}")
        
        # Componentes (consumos)
        raw_ids = mo.get('move_raw_ids', [])
        if raw_ids:
            consumos = client.search_read(
                'stock.move.line',
                [['move_id', 'in', raw_ids]],
                ['product_id', 'qty_done', 'lot_id'],
                limit=20
            )
            
            print(f"\n   📥 COMPONENTES ({len(consumos)}):")
            total_kg = 0
            for c in consumos:
                prod = c.get('product_id', [0, 'N/A'])
                qty = c.get('qty_done', 0) or 0
                total_kg += qty
                print(f"      • {prod[1][:50]} | {qty:,.2f} kg")
            print(f"      ─────────────────────────")
            print(f"      TOTAL: {total_kg:,.2f} kg")
        else:
            print(f"\n   📥 COMPONENTES: Sin move_raw_ids")
        
        # Subproductos (producción)
        finished_ids = mo.get('move_finished_ids', [])
        if finished_ids:
            produccion = client.search_read(
                'stock.move.line',
                [['move_id', 'in', finished_ids]],
                ['product_id', 'qty_done', 'lot_id'],
                limit=20
            )
            
            print(f"\n   📤 SUBPRODUCTOS ({len(produccion)}):")
            total_kg = 0
            for p in produccion:
                prod = p.get('product_id', [0, 'N/A'])
                qty = p.get('qty_done', 0) or 0
                total_kg += qty
                print(f"      • {prod[1][:50]} | {qty:,.2f} kg")
            print(f"      ─────────────────────────")
            print(f"      TOTAL: {total_kg:,.2f} kg")
        else:
            print(f"\n   📤 SUBPRODUCTOS: Sin move_finished_ids")


def debug_especie_manejo():
    """Verifica extracción de especie y manejo desde product.template."""
    print("\n" + "="*60)
    print("🏷️ DEBUG: ESPECIE Y MANEJO (product.template)")
    print("="*60)
    
    client = OdooClient(username=USERNAME, password=API_KEY)
    
    # Buscar productos con especie/manejo
    products = client.search_read(
        'product.template',
        [['x_studio_sub_categora', '!=', False]],
        ['id', 'name', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo'],
        limit=20
    )
    
    print(f"\n📋 Productos con x_studio_sub_categora configurado: {len(products)}")
    
    for p in products[:10]:
        especie = p.get('x_studio_sub_categora', '')
        if isinstance(especie, (list, tuple)) and len(especie) > 1:
            especie = especie[1]
        
        manejo = p.get('x_studio_categora_tipo_de_manejo', '')
        if isinstance(manejo, (list, tuple)) and len(manejo) > 1:
            manejo = manejo[1]
        
        print(f"  • {p['name'][:40]} | Especie: {especie} | Manejo: {manejo}")
    
    # Contar productos SIN especie/manejo
    products_sin = client.search(
        'product.template',
        [['x_studio_sub_categora', '=', False]]
    )
    print(f"\n⚠️ Productos SIN x_studio_sub_categora: {len(products_sin)}")


def debug_tuneles():
    """Verifica clasificación de túneles estáticos vs continuo."""
    print("\n" + "="*60)
    print("❄️ DEBUG: TÚNELES (Estáticos vs Continuo)")
    print("="*60)
    
    client = OdooClient(username=USERNAME, password=API_KEY)
    
    # Buscar todas las salas únicas
    mos = client.search_read(
        'mrp.production',
        [['state', '=', 'done']],
        ['x_studio_sala_de_proceso'],
        limit=1000
    )
    
    salas_set = set()
    for mo in mos:
        sala = mo.get('x_studio_sala_de_proceso') or ''
        if sala:
            salas_set.add(sala)
    
    print(f"\n📋 TODAS LAS SALAS ÚNICAS ({len(salas_set)}):")
    
    tuneles = []
    salas_proceso = []
    otros = []
    
    for sala in sorted(salas_set):
        sala_lower = sala.lower()
        if 'tunel' in sala_lower or 'túnel' in sala_lower or 'congela' in sala_lower:
            tuneles.append(sala)
        elif 'sala' in sala_lower or 'linea' in sala_lower or 'línea' in sala_lower:
            salas_proceso.append(sala)
        else:
            otros.append(sala)
    
    print(f"\n❄️ TÚNELES ({len(tuneles)}):")
    for t in tuneles:
        tipo = "Estático" if "estatico" in t.lower() or "estático" in t.lower() else "Continuo/Otro"
        print(f"  • {t} [{tipo}]")
    
    print(f"\n🏭 SALAS PROCESO ({len(salas_proceso)}):")
    for s in salas_proceso:
        print(f"  • {s}")
    
    print(f"\n❓ OTROS ({len(otros)}):")
    for o in otros:
        print(f"  • {o}")


def main():
    print("\n" + "="*60)
    print("🔍 DIAGNÓSTICO DE FABRICACIONES - RIO FUTURO")
    print(f"   Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    try:
        debug_filtro_planta()
        debug_componentes_subproductos()
        debug_especie_manejo()
        debug_tuneles()
        
        print("\n" + "="*60)
        print("✅ DIAGNÓSTICO COMPLETADO")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
