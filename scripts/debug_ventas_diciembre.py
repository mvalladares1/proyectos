#!/usr/bin/env python3
"""
Script para investigar ventas reales en diciembre 2025 y validar trazabilidad.
Solo cuenta pickings outgoing con origin que empieza con "S".
"""
import sys
sys.path.insert(0, '/home/feli/proyectos')

from shared.odoo_client import OdooClient
from backend.services.traceability.traceability_service import TraceabilityService
from datetime import datetime
import os
import time

# Configuración
username = os.getenv("ODOO_USERNAME", "frios@riofuturo.cl")
password = os.getenv("ODOO_API_KEY", "413c17f8c0a0ebe211cda26c094c2bbb47fce5c6")

if not password:
    print("Error: Define ODOO_API_KEY en el entorno")
    sys.exit(1)

client = OdooClient(username=username, password=password)

# Buscar pickings de diciembre 2025
print("=" * 80)
print("INVESTIGACIÓN: Ventas en Diciembre 2025")
print("=" * 80)

# Estrategia correcta: buscar sale.order por date_order
print("\nBuscando órdenes de venta por date_order...")
sale_orders = client.search_read(
    "sale.order",
    [
        ("state", "in", ["sale", "done"]),
        ("date_order", ">=", "2025-12-01 00:00:00"),
        ("date_order", "<=", "2025-12-31 23:59:59"),
    ],
    ["id", "name", "date_order", "partner_id"],
    limit=100
)

print(f"Órdenes de venta encontradas: {len(sale_orders)}")

# Mostrar las órdenes encontradas
print("\n" + "=" * 80)
print("ÓRDENES DE VENTA (sale.order):")
print("=" * 80)
for so in sale_orders:
    partner = so.get("partner_id", [False, ""])[1] if so.get("partner_id") else "Sin partner"
    date = so.get("date_order", "")[:10] if so.get("date_order") else "Sin fecha"
    print(f"{so['name']:15} | {date} | {partner}")

if not sale_orders:
    print("No se encontraron órdenes de venta en diciembre")
    sys.exit(0)

# Obtener los códigos de venta
sale_order_names = [so["name"] for so in sale_orders]

# Buscar pickings outgoing relacionados
print("\n" + "=" * 80)
print(f"Buscando pickings outgoing con origins: {', '.join(sale_order_names[:5])}{'...' if len(sale_order_names) > 5 else ''}")
print("=" * 80)
all_outgoing = client.search_read(
    "stock.picking",
    [
        ("picking_type_id.code", "=", "outgoing"),
        ("state", "=", "done"),
        ("origin", "in", sale_order_names)
    ],
    ["id", "name", "origin", "date_done", "scheduled_date"],
    limit=300
)

print(f"Pickings outgoing encontrados: {len(all_outgoing)}")

# Mostrar los pickings encontrados
print("\n" + "=" * 80)
print("PICKINGS OUTGOING RELACIONADOS:")
print("=" * 80)
for p in all_outgoing[:30]:  # Mostrar primeros 30
    origin = p.get("origin", "Sin origin")
    date_done = p.get("date_done", "")[:10] if p.get("date_done") else "Sin fecha"
    print(f"{p['name']:20} | Origin: {origin:15} | Done: {date_done}")

if len(all_outgoing) > 30:
    print(f"... y {len(all_outgoing) - 30} más")

print(f"\nTotal pickings outgoing: {len(all_outgoing)}")

# Filtrar solo los que tienen origin (debería ser todos en este caso)
ventas_reales = [p for p in all_outgoing if p.get("origin")]

print(f"Pickings con origin: {len(ventas_reales)}")
print("\n" + "=" * 80)
print("VENTAS ENCONTRADAS:")
print("=" * 80)

# Agrupar por origin
ventas_por_origin = {}
for v in ventas_reales:
    origin = v.get("origin", "")
    if origin not in ventas_por_origin:
        ventas_por_origin[origin] = []
    ventas_por_origin[origin].append(v)

print(f"\nTotal códigos de venta únicos: {len(ventas_por_origin)}")
print("\nDetalle por código de venta:")
print("-" * 80)

for origin in sorted(ventas_por_origin.keys()):
    pickings = ventas_por_origin[origin]
    print(f"\n{origin}:")
    for p in pickings:
        partner = p.get("partner_id", [False, ""])[1] if p.get("partner_id") else "Sin partner"
        print(f"  - {p['name']} | {p.get('date_done', '')[:10]} | {partner}")
    
    # Contar pallets de esta venta
    picking_ids = [p["id"] for p in pickings]
    move_lines = client.search_read(
        "stock.move.line",
        [
            ("picking_id", "in", picking_ids),
            ("package_id", "!=", False),
            ("qty_done", ">", 0),
            ("state", "=", "done"),
        ],
        ["package_id"],
        limit=500
    )
    
    package_ids = set()
    for ml in move_lines:
        pkg_rel = ml.get("package_id")
        if pkg_rel:
            pkg_id = pkg_rel[0] if isinstance(pkg_rel, (list, tuple)) else pkg_rel
            if pkg_id:
                package_ids.add(pkg_id)
    
    print(f"  Total pallets: {len(package_ids)}")

print("\n" + "=" * 80)
print("RESUMEN:")
print("=" * 80)
print(f"Órdenes de venta (sale.order) en diciembre: {len(sale_orders)}")
print(f"Pickings outgoing relacionados: {len(all_outgoing)}")
print(f"Códigos de venta únicos (origins): {len(ventas_por_origin)}")

# Contar pallets totales
all_picking_ids = [p["id"] for p in ventas_reales]
all_move_lines = client.search_read(
    "stock.move.line",
    [
        ("picking_id", "in", all_picking_ids),
        ("package_id", "!=", False),
        ("qty_done", ">", 0),
        ("state", "=", "done"),
    ],
    ["package_id"],
    limit=2000
)

total_packages = set()
for ml in all_move_lines:
    pkg_rel = ml.get("package_id")
    if pkg_rel:
        pkg_id = pkg_rel[0] if isinstance(pkg_rel, (list, tuple)) else pkg_rel
        if pkg_id:
            total_packages.add(pkg_id)

print(f"Total pallets en todas las ventas: {len(total_packages)}")
print("=" * 80)

# ========================================================================
# VALIDACIÓN DE TRAZABILIDAD
# ========================================================================
print("\n" + "=" * 80)
print("VALIDANDO TRAZABILIDAD CON EL FIX APLICADO")
print("=" * 80)

# Inicializar servicio de trazabilidad (reusa el mismo client)
traz_service = TraceabilityService(username=username, password=password)

# Obtener IDs de paquetes para trazar
package_ids_list = list(total_packages)
print(f"\nPaquetes a trazar: {len(package_ids_list)}")

# Ejecutar trazabilidad con include_siblings=False (modo directo)
print("\n➤ Ejecutando trazabilidad hacia atrás (include_siblings=False)...")
start_time = time.time()

try:
    result = traz_service._get_traceability_for_packages(
        initial_package_ids=package_ids_list,
        limit=10000,
        include_siblings=False
    )
    
    elapsed = time.time() - start_time
    
    print(f"✓ Trazabilidad completada en {elapsed:.2f} segundos")
    print("\n" + "=" * 80)
    print("RESULTADOS DE TRAZABILIDAD:")
    print("=" * 80)
    
    # Analizar resultados
    all_pallets = result.get("pallets", {})
    all_processes = result.get("processes", {})
    all_suppliers = result.get("suppliers", {})
    all_links = result.get("links", [])
    
    print(f"\nPallets totales: {len(all_pallets)}")
    print(f"Procesos totales: {len(all_processes)}")
    print(f"Proveedores totales: {len(all_suppliers)}")
    print(f"Links totales: {len(all_links)}")
    
    # Agrupar procesos por tipo
    processes_by_origin = {}
    for proc_id, proc_data in all_processes.items():
        origin = proc_data.get("origin", "Sin origin")
        if origin not in processes_by_origin:
            processes_by_origin[origin] = []
        processes_by_origin[origin].append(proc_data)
    
    print(f"\nOrgenes de procesos encontrados: {len(processes_by_origin)}")
    print("\nTop 10 procesos por cantidad:")
    print("-" * 80)
    sorted_origins = sorted(processes_by_origin.items(), key=lambda x: len(x[1]), reverse=True)
    for origin, procs in sorted_origins[:10]:
        print(f"  {origin}: {len(procs)} procesos")
        # Verificar si alguno es RF/INT/ (debería estar excluido)
        if "RF/INT/" in origin:
            print(f"    ⚠️  ALERTA: Proceso RF/INT/ encontrado (debería estar excluido)")
    
    # Contar inputs/outputs por proceso
    print("\n" + "=" * 80)
    print("ANÁLISIS DE INPUTS/OUTPUTS:")
    print("=" * 80)
    
    # Los links pueden ser tuplas o diccionarios dependiendo del formato
    process_stats = {}
    for link in all_links:
        # Si es tupla, convertir a dict
        if isinstance(link, tuple):
            # Formato: (tipo, source, target, ...) o similar
            if len(link) >= 3:
                source = str(link[1]) if len(link) > 1 else ""
                target = str(link[2]) if len(link) > 2 else ""
            else:
                continue
        else:
            source = link.get("source", "")
            target = link.get("target", "")
        
        # Identificar si empieza con PROCESS:
        if source and "PROCESS:" in str(source):
            # Este proceso tiene un output
            if source not in process_stats:
                process_stats[source] = {"inputs": 0, "outputs": 0}
            process_stats[source]["outputs"] += 1
        
        if target and "PROCESS:" in str(target):
            # Este proceso tiene un input
            if target not in process_stats:
                process_stats[target] = {"inputs": 0, "outputs": 0}
            process_stats[target]["inputs"] += 1
    
    # Top procesos por inputs
    print("\nTop 10 procesos con más inputs:")
    print("-" * 80)
    sorted_by_inputs = sorted(process_stats.items(), key=lambda x: x[1]["inputs"], reverse=True)
    for proc_id, stats in sorted_by_inputs[:10]:
        proc_data = all_processes.get(proc_id, {})
        origin = proc_data.get("origin", "Sin origin")
        print(f"  {origin}: {stats['inputs']} inputs, {stats['outputs']} outputs")
    
    print("\n" + "=" * 80)
    print("VALIDACIÓN COMPLETADA")
    print("=" * 80)
    print(f"\n✓ Tiempo de ejecución: {elapsed:.2f} segundos")
    print(f"✓ Resultado esperado: ~200-500 pallets, ~50-100 procesos")
    print(f"✓ Resultado obtenido: {len(all_pallets)} pallets, {len(all_processes)} procesos")
    
    if len(all_pallets) > 1000:
        print("\n⚠️  ALERTA: Demasiados pallets. El fix puede no estar funcionando correctamente.")
    elif len(all_processes) > 200:
        print("\n⚠️  ADVERTENCIA: Muchos procesos. Revisar si hay expansión innecesaria.")
    else:
        print("\n✓ Los números lucen razonables. El fix parece estar funcionando.")

except Exception as e:
    print(f"\n❌ Error en trazabilidad: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
