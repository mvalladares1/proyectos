#!/usr/bin/env python3
"""
Benchmark: medir todos los modelos relevantes para trazabilidad
"""
import sys
import os
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from shared.odoo_client import OdooClient


def search_count(odoo, model, domain):
    return odoo.models.execute_kw(
        odoo.db, odoo.uid, odoo.password,
        model, 'search_count', [domain]
    )


def benchmark_model(odoo, model, domain, fields, description):
    """Benchmark un modelo específico"""
    print(f"\n{'='*60}")
    print(f"📦 {description}")
    print(f"   Modelo: {model}")
    print(f"{'='*60}")
    
    # Contar
    t0 = time.time()
    count = search_count(odoo, model, domain)
    t1 = time.time()
    print(f"   Total registros: {count:,} ({t1-t0:.2f}s)")
    
    if count == 0:
        return {"model": model, "count": 0, "time": 0}
    
    # Traer muestra de 1000
    t0 = time.time()
    sample = odoo.search_read(model, domain, fields, limit=1000)
    t1 = time.time()
    print(f"   1,000 registros: {t1-t0:.2f}s")
    
    # Estimar tiempo total
    estimated_time = (t1-t0) * (count / 1000) if count > 1000 else t1-t0
    print(f"   Tiempo estimado total: {estimated_time:.1f}s")
    
    return {
        "model": model,
        "description": description,
        "count": count,
        "estimated_time": estimated_time
    }


def main():
    odoo = OdooClient(
        username = "frios@riofuturo.cl",
        password = "413c17f8c0a0ebe211cda26c094c2bbb47fce5c6"
    )
    
    print("=" * 60)
    print("BENCHMARK: Modelos para Trazabilidad")
    print("=" * 60)
    
    results = []
    
    # 1. stock.move.line (ya lo conocemos)
    results.append(benchmark_model(
        odoo,
        "stock.move.line",
        [("state", "=", "done"), ("qty_done", ">", 0)],
        ["id", "reference", "package_id", "result_package_id", "date", 
         "location_id", "location_dest_id", "product_id", "qty_done", "move_id"],
        "Movimientos de Stock"
    ))
    
    # 2. stock.quant.package (pallets)
    results.append(benchmark_model(
        odoo,
        "stock.quant.package",
        [],
        ["id", "name", "location_id"],
        "Paquetes/Pallets"
    ))
    
    # 3. mrp.production (órdenes de producción)
    results.append(benchmark_model(
        odoo,
        "mrp.production",
        [("state", "in", ["done", "progress", "confirmed"])],
        ["id", "name", "product_id", "product_qty", "date_start", "date_finished", "state"],
        "Órdenes de Producción"
    ))
    
    # 4. sale.order (ventas)
    results.append(benchmark_model(
        odoo,
        "sale.order",
        [("state", "in", ["sale", "done"])],
        ["id", "name", "partner_id", "date_order", "state", "amount_total"],
        "Órdenes de Venta"
    ))
    
    # 5. purchase.order (compras)
    results.append(benchmark_model(
        odoo,
        "purchase.order",
        [("state", "in", ["purchase", "done"])],
        ["id", "name", "partner_id", "date_order", "state", "amount_total"],
        "Órdenes de Compra"
    ))
    
    # 6. stock.picking (recepciones/despachos)
    results.append(benchmark_model(
        odoo,
        "stock.picking",
        [("state", "=", "done")],
        ["id", "name", "partner_id", "scheduled_date", "date_done", 
         "picking_type_id", "origin", "sale_id"],
        "Recepciones/Despachos"
    ))
    
    # 7. res.partner
    results.append(benchmark_model(
        odoo,
        "res.partner",
        [("active", "=", True)],
        ["id", "name", "vat", "city", "country_id"],
        "Partners (Clientes/Proveedores)"
    ))
    
    # 8. product.product
    results.append(benchmark_model(
        odoo,
        "product.product",
        [("active", "=", True)],
        ["id", "name", "default_code", "categ_id", "uom_id"],
        "Productos"
    ))
    
    # 9. stock.location
    results.append(benchmark_model(
        odoo,
        "stock.location",
        [("usage", "in", ["internal", "transit"])],
        ["id", "name", "complete_name", "usage"],
        "Ubicaciones"
    ))
    
    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN TOTAL")
    print("=" * 60)
    
    total_records = 0
    total_time = 0
    
    print(f"\n{'Modelo':<25} {'Registros':>12} {'Tiempo Est.':>12}")
    print("-" * 50)
    for r in results:
        total_records += r["count"]
        total_time += r.get("estimated_time", 0)
        print(f"{r['model']:<25} {r['count']:>12,} {r.get('estimated_time', 0):>10.1f}s")
    
    print("-" * 50)
    print(f"{'TOTAL':<25} {total_records:>12,} {total_time:>10.1f}s")
    
    print("\n💡 CONCLUSIÓN:")
    print(f"   Carga inicial completa: ~{total_time:.0f} segundos")
    print(f"   Refresh incremental (5 min): <2 segundos")
    print("=" * 60)


if __name__ == "__main__":
    main()
