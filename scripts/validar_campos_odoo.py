"""
Script de Validación: Sistema Rio Futuro
==========================================

Valida que los campos custom existen y están correctamente configurados.
"""

import sys
import os

# Agregar el directorio raíz al path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient

# ============================================
# CONFIGURACIÓN
# ============================================

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = None  # Se pedirá interactivamente


def test_conexion_odoo():
    """Test 1: Verificar conexión a Odoo"""
    print("\n" + "=" * 70)
    print("TEST 1: Conexión a Odoo")
    print("=" * 70)
    
    global PASSWORD
    if not PASSWORD:
        import getpass
        PASSWORD = getpass.getpass(f"API Key para {USERNAME}: ")
    
    odoo = OdooClient()
    
    try:
        odoo.authenticate(USERNAME, PASSWORD)
        print(f"✅ Conectado exitosamente")
        print(f"   UID: {odoo.uid}")
        print(f"   Database: {odoo.db}")
        return odoo
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return None


def test_campos_mrp_production(odoo):
    """Test 2: Verificar campos custom en mrp.production"""
    print("\n" + "=" * 70)
    print("TEST 2: Campos custom en mrp.production")
    print("=" * 70)
    
    try:
        fields = odoo.models.execute_kw(
            odoo.db, odoo.uid, odoo.password,
            'mrp.production', 'fields_get',
            [],
            {'attributes': ['string', 'type', 'relation']}
        )
        
        campos_esperados = [
            'x_studio_po_asociada_1',
            'x_studio_kg_totales_po',
            'x_studio_kg_consumidos_po',
            'x_studio_kg_disponibles_po',
            'x_studio_productos_po_resumen'
        ]
        
        print("\n📋 Campos custom encontrados:")
        encontrados = 0
        
        for campo in campos_esperados:
            if campo in fields:
                info = fields[campo]
                print(f"   ✅ {campo}")
                print(f"      Tipo: {info.get('type')}")
                print(f"      Label: {info.get('string')}")
                if info.get('relation'):
                    print(f"      Relación: {info.get('relation')}")
                encontrados += 1
            else:
                print(f"   ❌ {campo} - NO ENCONTRADO")
        
        print(f"\n📊 Resultado: {encontrados}/{len(campos_esperados)} campos encontrados")
        return encontrados == len(campos_esperados)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_campos_stock_move_line(odoo):
    """Test 3: Verificar x_studio_so_linea en stock.move.line"""
    print("\n" + "=" * 70)
    print("TEST 3: Campo x_studio_so_linea en stock.move.line")
    print("=" * 70)
    
    try:
        fields = odoo.models.execute_kw(
            odoo.db, odoo.uid, odoo.password,
            'stock.move.line', 'fields_get',
            ['x_studio_so_linea'],
            {'attributes': ['string', 'type', 'relation']}
        )
        
        if 'x_studio_so_linea' in fields:
            info = fields['x_studio_so_linea']
            print(f"\n✅ Campo x_studio_so_linea ENCONTRADO")
            print(f"   Tipo: {info.get('type')}")
            print(f"   Label: {info.get('string')}")
            print(f"   Relación: {info.get('relation')}")
            
            # Verificar que apunta a sale.order.line
            if info.get('relation') == 'sale.order.line':
                print(f"   ✅ Relación correcta (sale.order.line)")
                return True
            else:
                print(f"   ⚠️  Relación inesperada: {info.get('relation')}")
                print(f"   ℹ️  Se esperaba: sale.order.line")
                return False
        else:
            print(f"\n❌ Campo x_studio_so_linea NO encontrado")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_leer_odf_ejemplo(odoo):
    """Test 4: Leer una ODF de ejemplo"""
    print("\n" + "=" * 70)
    print("TEST 4: Leer ODF de ejemplo")
    print("=" * 70)
    
    try:
        # Buscar ODFs recientes
        odfs = odoo.search_read(
            'mrp.production',
            [['state', '=', 'done']],
            ['name', 'product_id', 'date_start', 'x_studio_po_asociada_1'],
            limit=5
        )
        
        if not odfs:
            print("⚠️  No se encontraron ODFs en estado 'done'")
            return False
        
        print(f"\n📦 Últimas {len(odfs)} ODFs encontradas:")
        print("-" * 70)
        
        for odf in odfs:
            print(f"\n   ID: {odf['id']}")
            print(f"   Nombre: {odf.get('name', 'N/A')}")
            print(f"   Producto: {odf.get('product_id', ['', 'N/A'])[1] if odf.get('product_id') else 'N/A'}")
            print(f"   Fecha inicio: {odf.get('date_start', 'N/A')}")
            
            if odf.get('x_studio_po_asociada_1'):
                po_info = odf['x_studio_po_asociada_1']
                print(f"   PO Asociada: {po_info[1] if isinstance(po_info, (list, tuple)) else po_info}")
            else:
                print(f"   PO Asociada: Sin asignar")
        
        # Preguntar si quiere analizar una
        print("\n" + "-" * 70)
        odf_id = input("\n¿Quieres analizar alguna de estas ODFs? (ingresa ID o Enter para saltar): ")
        
        if odf_id and odf_id.isdigit():
            return test_analizar_consumos(odoo, int(odf_id))
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_analizar_consumos(odoo, odf_id):
    """Test 5: Analizar consumos de una ODF específica"""
    print("\n" + "=" * 70)
    print(f"TEST 5: Analizar consumos de ODF #{odf_id}")
    print("=" * 70)
    
    try:
        # Leer consumos
        consumos = odoo.search_read(
            'stock.move.line',
            [
                ['production_id', '=', odf_id],
                ['state', '=', 'done']
            ],
            ['date', 'product_id', 'qty_done', 'x_studio_so_linea']
        )
        
        if not consumos:
            print(f"⚠️  No se encontraron consumos para ODF #{odf_id}")
            return False
        
        print(f"\n📊 {len(consumos)} consumos encontrados")
        print("-" * 70)
        
        # Agrupar por SO
        so_agrupado = {}
        consumos_sin_so = []
        
        for consumo in consumos:
            so_linea = consumo.get('x_studio_so_linea')
            
            if so_linea:
                # Obtener sale_order desde sale_order_line
                so_line_id = so_linea[0] if isinstance(so_linea, (list, tuple)) else so_linea
                
                # Buscar order_id
                so_line_data = odoo.search_read(
                    'sale.order.line',
                    [['id', '=', so_line_id]],
                    ['order_id']
                )
                
                if so_line_data and so_line_data[0].get('order_id'):
                    order_id = so_line_data[0]['order_id'][0]
                    order_name = so_line_data[0]['order_id'][1]
                    
                    if order_id not in so_agrupado:
                        so_agrupado[order_id] = {
                            'nombre': order_name,
                            'kg_total': 0,
                            'consumos': 0
                        }
                    
                    so_agrupado[order_id]['kg_total'] += consumo.get('qty_done', 0)
                    so_agrupado[order_id]['consumos'] += 1
                else:
                    consumos_sin_so.append(consumo)
            else:
                consumos_sin_so.append(consumo)
        
        # Mostrar resultados
        if so_agrupado:
            print("\n✅ Consumos por Sale Order:")
            print("-" * 70)
            for so_id, data in so_agrupado.items():
                print(f"   {data['nombre']}:")
                print(f"      • Kg consumidos: {data['kg_total']:,.2f}")
                print(f"      • Nº consumos: {data['consumos']}")
        else:
            print("\n⚠️  No hay consumos con x_studio_so_linea asignado")
        
        if consumos_sin_so:
            print(f"\n⚠️  {len(consumos_sin_so)} consumos SIN sale order asignada")
        
        # Primeros 3 consumos raw
        print("\n📋 Primeros 3 consumos (detalle):")
        print("-" * 70)
        for i, c in enumerate(consumos[:3], 1):
            print(f"\n   Consumo {i}:")
            print(f"      Fecha: {c.get('date', 'N/A')}")
            print(f"      Producto: {c.get('product_id', ['', 'N/A'])[1] if c.get('product_id') else 'N/A'}")
            print(f"      Cantidad: {c.get('qty_done', 0):,.2f} kg")
            
            if c.get('x_studio_so_linea'):
                so_linea = c['x_studio_so_linea']
                print(f"      SO Line: {so_linea[1] if isinstance(so_linea, (list, tuple)) else so_linea}")
            else:
                print(f"      SO Line: ❌ Sin asignar")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Ejecuta todos los tests"""
    print("\n" + "=" * 70)
    print("VALIDACIÓN: SISTEMA RIO FUTURO")
    print("=" * 70)
    
    # Test 1: Conexión
    odoo = test_conexion_odoo()
    if not odoo:
        print("\n❌ No se pudo conectar a Odoo. Abortando.")
        return
    
    # Test 2: Campos mrp.production
    test_campos_mrp_production(odoo)
    
    # Test 3: Campo x_studio_so_linea
    campo_ok = test_campos_stock_move_line(odoo)
    
    if not campo_ok:
        print("\n" + "=" * 70)
        print("⚠️  ADVERTENCIA")
        print("=" * 70)
        print("\nEl campo x_studio_so_linea no existe o no está configurado correctamente.")
        print("\nPara que el sistema funcione, necesitas:")
        print("1. Crear el campo en Odoo Studio")
        print("2. Tipo: Many2one")
        print("3. Relación: sale.order.line")
        print("4. Agregarlo a las vistas de consumo")
        print("\n" + "=" * 70)
        return
    
    # Test 4: Leer ODFs
    test_leer_odf_ejemplo(odoo)
    
    print("\n" + "=" * 70)
    print("✅ VALIDACIÓN COMPLETADA")
    print("=" * 70)


if __name__ == "__main__":
    main()
