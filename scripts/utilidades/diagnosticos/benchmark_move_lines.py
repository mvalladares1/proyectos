#!/usr/bin/env python3
"""
Benchmark: medir tiempo de consulta a stock.move.line
"""
import sys
import os
import time

# Agregar raíz del proyecto al path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from shared.odoo_client import OdooClient


def benchmark():
    username = "frios@riofuturo.cl"
    password = "413c17f8c0a0ebe211cda26c094c2bbb47fce5c6"
    
    if not username or not password:
        print("❌ Falta ODOO_USER y/o ODOO_PASSWORD en variables de entorno")
        return
    
    odoo = OdooClient(username=username, password=password)
    
    # Función helper para search_count (no existe en OdooClient)
    def search_count(model, domain):
        return odoo.models.execute_kw(
            odoo.db, odoo.uid, odoo.password,
            model, 'search_count', [domain]
        )
    
    print("=" * 60)
    print("BENCHMARK: stock.move.line")
    print("=" * 60)
    
    # 1. Contar registros totales
    print("\n📊 Contando registros totales...")
    t0 = time.time()
    total_count = search_count("stock.move.line", [])
    t1 = time.time()
    print(f"   Total registros: {total_count:,}")
    print(f"   Tiempo count: {t1-t0:.2f}s")
    
    # 2. Contar con filtros típicos de trazabilidad
    print("\n📊 Contando con filtros de trazabilidad...")
    t0 = time.time()
    filtered_count = search_count(
        "stock.move.line",
        [
            ("state", "=", "done"),
            ("qty_done", ">", 0),
            "|",
            ("package_id", "!=", False),
            ("result_package_id", "!=", False),
        ]
    )
    t1 = time.time()
    print(f"   Registros filtrados: {filtered_count:,}")
    print(f"   Tiempo count filtrado: {t1-t0:.2f}s")
    
    # 3. Traer 1000 registros (campos mínimos)
    print("\n📊 Trayendo 1,000 registros (campos mínimos)...")
    t0 = time.time()
    records = odoo.search_read(
        "stock.move.line",
        [("state", "=", "done"), ("qty_done", ">", 0)],
        ["id", "reference", "package_id", "result_package_id", "date"],
        limit=1000
    )
    t1 = time.time()
    print(f"   Registros obtenidos: {len(records):,}")
    print(f"   Tiempo: {t1-t0:.2f}s")
    
    # 4. Traer 10,000 registros
    print("\n📊 Trayendo 10,000 registros (campos mínimos)...")
    t0 = time.time()
    records = odoo.search_read(
        "stock.move.line",
        [("state", "=", "done"), ("qty_done", ">", 0)],
        ["id", "reference", "package_id", "result_package_id", "date"],
        limit=10000
    )
    t1 = time.time()
    print(f"   Registros obtenidos: {len(records):,}")
    print(f"   Tiempo: {t1-t0:.2f}s")
    
    # 5. Traer 50,000 registros
    print("\n📊 Trayendo 50,000 registros (campos mínimos)...")
    t0 = time.time()
    records = odoo.search_read(
        "stock.move.line",
        [("state", "=", "done"), ("qty_done", ">", 0)],
        ["id", "reference", "package_id", "result_package_id", "date"],
        limit=50000
    )
    t1 = time.time()
    print(f"   Registros obtenidos: {len(records):,}")
    print(f"   Tiempo: {t1-t0:.2f}s")
    
    # 6. Traer con filtro de trazabilidad (con paquetes)
    print("\n📊 Trayendo 50,000 registros CON paquetes...")
    t0 = time.time()
    records = odoo.search_read(
        "stock.move.line",
        [
            ("state", "=", "done"),
            ("qty_done", ">", 0),
            "|",
            ("package_id", "!=", False),
            ("result_package_id", "!=", False),
        ],
        ["id", "reference", "package_id", "result_package_id", "date", "location_id", "location_dest_id"],
        limit=50000
    )
    t1 = time.time()
    print(f"   Registros obtenidos: {len(records):,}")
    print(f"   Tiempo: {t1-t0:.2f}s")
    
    # 7. Traer TODOS los registros con paquetes EN BATCHES
    print(f"\n📊 Trayendo TODOS los {filtered_count:,} registros en batches de 30,000...")
    domain = [
        ("state", "=", "done"),
        ("qty_done", ">", 0),
        "|",
        ("package_id", "!=", False),
        ("result_package_id", "!=", False),
    ]
    fields = ["id", "reference", "package_id", "result_package_id", "date", "location_id", "location_dest_id"]
    
    BATCH_SIZE = 30000
    all_records = []
    offset = 0
    t0 = time.time()
    
    while True:
        batch_start = time.time()
        batch = odoo.search_read(
            "stock.move.line",
            domain,
            fields,
            limit=BATCH_SIZE,
            order="id asc"
        )
        # Para offset necesitamos filtrar por ID > último
        if not batch:
            break
        all_records.extend(batch)
        batch_time = time.time() - batch_start
        print(f"   Batch {len(all_records)//BATCH_SIZE}: {len(batch):,} registros en {batch_time:.2f}s")
        
        if len(batch) < BATCH_SIZE:
            break
        
        # Siguiente batch: filtrar por ID mayor al último
        last_id = batch[-1]["id"]
        domain = [
            ("state", "=", "done"),
            ("qty_done", ">", 0),
            ("id", ">", last_id),
            "|",
            ("package_id", "!=", False),
            ("result_package_id", "!=", False),
        ]
    
    t1 = time.time()
    print(f"\n   ✅ Total obtenidos: {len(all_records):,}")
    print(f"   ⏱️  Tiempo total: {t1-t0:.2f}s")
    print(f"   🚀 Velocidad: {len(all_records)/(t1-t0):.0f} registros/segundo")
    
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"  - Total stock.move.line: {total_count:,}")
    print(f"  - Con paquetes (trazabilidad): {filtered_count:,}")
    print(f"  - Tiempo para traer TODO: {t1-t0:.1f}s")
    print("=" * 60)


if __name__ == "__main__":
    benchmark()
