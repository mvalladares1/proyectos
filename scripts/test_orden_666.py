"""
Script de prueba para consultar clasificación de la orden WH/Transf/00666
"""
import sys
import os

# Añadir paths necesarios
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.produccion_service import ProduccionService

# Credenciales
ODOO_USERNAME = "mjaramillo@riofuturo.cl"
ODOO_PASSWORD = "659e9fd07b2bc2c0aca3539de16a9da50bb263b1"

def test_orden_666():
    """Prueba la clasificación para WH/Transf/00666"""
    
    print("=" * 80)
    print("CONSULTANDO CLASIFICACIÓN - ORDEN: WH/Transf/00666")
    print("=" * 80)
    
    # Crear servicio
    service = ProduccionService(username=ODOO_USERNAME, password=ODOO_PASSWORD)
    
    # Consultar clasificación SIN FILTRO DE FECHA, solo por orden
    # Usamos fechas muy amplias que abarquen todo
    fecha_inicio = "2020-01-01"
    fecha_fin = "2030-12-31"
    orden = "WH/Transf/00666"
    
    print(f"\nBuscando SOLO por orden: {orden}")
    print(f"(Sin filtro de fecha - rango amplio: {fecha_inicio} a {fecha_fin})")
    print(f"Consultando Odoo...\n")
    
    try:
        result = service.get_clasificacion_pallets(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            tipo_fruta=None,
            tipo_manejo=None,
            orden_fabricacion=orden
        )
        
        print("CONSULTA EXITOSA\n")
        print("=" * 80)
        print("RESULTADOS - TOTALES POR GRADO")
        print("=" * 80)
        
        grados = result.get('grados', {})
        print(f"1 - IQF AA:      {grados.get('1', 0):>12,.2f} kg")
        print(f"2 - IQF A:       {grados.get('2', 0):>12,.2f} kg")
        print(f"3 - PSP:         {grados.get('3', 0):>12,.2f} kg")
        print(f"4 - W&B:         {grados.get('4', 0):>12,.2f} kg")
        print(f"5 - Block:       {grados.get('5', 0):>12,.2f} kg")
        print(f"6 - Jugo:        {grados.get('6', 0):>12,.2f} kg")
        print(f"7 - IQF Retail:  {grados.get('7', 0):>12,.2f} kg")
        print("-" * 80)
        print(f"TOTAL:           {result.get('total_kg', 0):>12,.2f} kg")
        
        print("\n" + "=" * 80)
        print(f"DETALLE - {len(result.get('detalle', []))} PRODUCTOS CLASIFICADOS")
        print("=" * 80)
        
        if result.get('detalle'):
            # Mostrar tabla
            print(f"\n{'Producto':<40} {'Codigo':<12} {'Grado':<15} {'Kg':>10}")
            print("-" * 80)
            
            for item in result['detalle'][:20]:  # Primeros 20
                print(f"{item['producto'][:39]:<40} {item.get('codigo_producto', 'N/A'):<12} "
                      f"{item.get('grado', 'N/A'):<15} {item['kg']:>10,.2f}")
            
            if len(result['detalle']) > 20:
                print(f"\n... y {len(result['detalle']) - 20} productos mas")
            
            # Resumen por grado
            print("\n" + "=" * 80)
            print("RESUMEN POR GRADO")
            print("=" * 80)
            
            GRADO_NOMBRES = {
                '1': 'IQF AA',
                '2': 'IQF A',
                '3': 'PSP',
                '4': 'W&B',
                '5': 'Block',
                '6': 'Jugo',
                '7': 'IQF Retail'
            }
            
            for grado_num, grado_nombre in GRADO_NOMBRES.items():
                kg = grados.get(grado_num, 0)
                if kg > 0:
                    productos = [p for p in result['detalle'] if p.get('grado') == grado_nombre]
                    print(f"\n{grado_nombre}:")
                    print(f"   Productos: {len(productos)}")
                    print(f"   Kg Total: {kg:,.2f} kg")
                    if productos:
                        print(f"   Kg Promedio/producto: {kg / len(productos):,.2f} kg")
                        codigos = set(p.get('codigo_producto', 'N/A') for p in productos)
                        print(f"   Codigos unicos: {codigos}")
        else:
            print("\nNo se encontraron productos clasificados para esta orden")
            print("   Posibles razones:")
            print("   - La orden no tiene productos con grados de 1 a 7")
            print("   - La orden no tiene stock.move con quantity_done")
            print("   - La orden no esta en el rango de fechas especificado")
            print("   - La orden esta cancelada")
        
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        print("\nTraceback completo:")
        traceback.print_exc()


if __name__ == "__main__":
    test_orden_666()
