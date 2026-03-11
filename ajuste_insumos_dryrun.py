#!/usr/bin/env python3
"""
AJUSTE DE INSUMOS - MODO DRY RUN
================================
Permite ver toda la repercusión de un ajuste antes de ejecutarlo.

Uso:
    python ajuste_insumos_dryrun.py --code 500000-24 --qty 1500
    python ajuste_insumos_dryrun.py --code 500000-24 --qty 1500 --execute  # Para ejecutar realmente
"""

import xmlrpc.client
import argparse
from datetime import datetime, timedelta
from collections import defaultdict
import json

# Configuración Odoo
URL = "https://riofuturo.server98c6e.oerpondemand.net"
DB = "riofuturo-master"
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

# Ubicaciones RF/Insumos
RF_INSUMOS_LOCATION_ID = 24  # RF/Insumos/Bodega Insumos
RF_INSUMOS_PARENT_ID = 5474  # RF/Insumos (padre)

# Ubicación de pérdida de inventario (para ajustes negativos)
INVENTORY_LOSS_LOCATION_ID = 5  # Virtual Locations/Inventory adjustment


class AjusteInsumosDryRun:
    def __init__(self):
        self.common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
        self.uid = self.common.authenticate(DB, USERNAME, PASSWORD, {})
        self.models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
        
        if not self.uid:
            raise Exception("Error de autenticación")
        
        print(f"✓ Conectado a Odoo como usuario {self.uid}")
    
    def buscar_producto(self, default_code: str) -> dict:
        """Busca producto por default_code"""
        products = self.models.execute_kw(
            DB, self.uid, PASSWORD,
            'product.product', 'search_read',
            [[('default_code', '=', default_code)]],
            {'fields': ['id', 'name', 'default_code', 'categ_id', 'uom_id', 
                       'standard_price', 'type', 'active']}
        )
        
        if not products:
            # Intentar búsqueda parcial
            products = self.models.execute_kw(
                DB, self.uid, PASSWORD,
                'product.product', 'search_read',
                [[('default_code', 'ilike', default_code)]],
                {'fields': ['id', 'name', 'default_code', 'categ_id', 'uom_id',
                           'standard_price', 'type', 'active'],
                 'limit': 5}
            )
            if products:
                print(f"\n⚠️ No se encontró código exacto '{default_code}'. Posibles coincidencias:")
                for p in products:
                    print(f"   [{p['default_code']}] {p['name']}")
                return None
            return None
        
        return products[0]
    
    def obtener_stock_rf_insumos(self, product_id: int) -> dict:
        """Obtiene stock actual del producto en ubicaciones RF/Insumos"""
        # Buscar todas las ubicaciones bajo RF/Insumos
        locations = self.models.execute_kw(
            DB, self.uid, PASSWORD,
            'stock.location', 'search',
            [[('id', 'child_of', RF_INSUMOS_PARENT_ID), ('usage', '=', 'internal')]]
        )
        
        # Obtener quants en esas ubicaciones
        quants = self.models.execute_kw(
            DB, self.uid, PASSWORD,
            'stock.quant', 'search_read',
            [[('product_id', '=', product_id), ('location_id', 'in', locations)]],
            {'fields': ['location_id', 'quantity', 'reserved_quantity', 'lot_id']}
        )
        
        total_qty = sum(q['quantity'] for q in quants)
        total_reserved = sum(q['reserved_quantity'] for q in quants)
        
        return {
            'quants': quants,
            'total_quantity': total_qty,
            'total_reserved': total_reserved,
            'disponible': total_qty - total_reserved,
            'locations': locations
        }
    
    def obtener_movimientos_recientes(self, product_id: int, locations: list, dias: int = 30) -> list:
        """Obtiene movimientos recientes del producto"""
        fecha_desde = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')
        
        moves = self.models.execute_kw(
            DB, self.uid, PASSWORD,
            'stock.move', 'search_read',
            [[
                ('product_id', '=', product_id),
                ('state', '=', 'done'),
                ('date', '>=', fecha_desde),
                '|',
                ('location_id', 'in', locations),
                ('location_dest_id', 'in', locations)
            ]],
            {'fields': ['date', 'location_id', 'location_dest_id', 'quantity_done', 
                       'picking_id', 'origin', 'reference'],
             'order': 'date desc',
             'limit': 20}
        )
        
        return moves
    
    def obtener_pickings_pendientes(self, product_id: int, locations: list) -> list:
        """Obtiene pickings con reservas pendientes"""
        moves = self.models.execute_kw(
            DB, self.uid, PASSWORD,
            'stock.move', 'search_read',
            [[
                ('product_id', '=', product_id),
                ('state', 'in', ['assigned', 'partially_available', 'waiting', 'confirmed']),
                '|',
                ('location_id', 'in', locations),
                ('location_dest_id', 'in', locations)
            ]],
            {'fields': ['picking_id', 'product_uom_qty', 'quantity_done', 'state', 
                       'location_id', 'location_dest_id']}
        )
        
        return moves
    
    def calcular_impacto(self, product: dict, stock_actual: float, qty_fisica: float) -> dict:
        """Calcula el impacto del ajuste"""
        diferencia = qty_fisica - stock_actual
        
        # Impacto contable estimado
        costo_unitario = product.get('standard_price', 0)
        impacto_valor = diferencia * costo_unitario
        
        return {
            'stock_sistema': stock_actual,
            'stock_fisico': qty_fisica,
            'diferencia': diferencia,
            'tipo_ajuste': 'ENTRADA' if diferencia > 0 else 'SALIDA' if diferencia < 0 else 'SIN CAMBIO',
            'costo_unitario': costo_unitario,
            'impacto_valor': impacto_valor,
            'impacto_valor_abs': abs(impacto_valor)
        }
    
    def generar_reporte_dryrun(self, default_code: str, qty_fisica: float) -> dict:
        """Genera reporte completo de dry run"""
        
        print("\n" + "="*70)
        print(f"  ANÁLISIS DE AJUSTE - DRY RUN")
        print(f"  Código: {default_code} | Cantidad física reportada: {qty_fisica}")
        print("="*70)
        
        # 1. Buscar producto
        print("\n[1/5] Buscando producto...")
        producto = self.buscar_producto(default_code)
        
        if not producto:
            print(f"\n❌ ERROR: Producto con código '{default_code}' no encontrado")
            return None
        
        print(f"   ✓ Encontrado: [{producto['default_code']}] {producto['name']}")
        print(f"   • ID: {producto['id']}")
        print(f"   • Categoría: {producto['categ_id'][1] if producto['categ_id'] else 'N/A'}")
        print(f"   • UdM: {producto['uom_id'][1] if producto['uom_id'] else 'N/A'}")
        print(f"   • Costo estándar: ${producto.get('standard_price', 0):,.2f}")
        print(f"   • Tipo: {producto.get('type', 'N/A')}")
        print(f"   • Activo: {'Sí' if producto.get('active') else 'No'}")
        
        # 2. Obtener stock actual
        print("\n[2/5] Obteniendo stock en RF/Insumos...")
        stock_info = self.obtener_stock_rf_insumos(producto['id'])
        
        print(f"   • Ubicaciones analizadas: {len(stock_info['locations'])}")
        print(f"   • Quants encontrados: {len(stock_info['quants'])}")
        
        if stock_info['quants']:
            print("\n   Detalle por ubicación:")
            for q in stock_info['quants']:
                loc_name = q['location_id'][1] if q['location_id'] else 'N/A'
                lot_name = q['lot_id'][1] if q['lot_id'] else 'Sin lote'
                reservado = f" (reservado: {q['reserved_quantity']})" if q['reserved_quantity'] > 0 else ""
                print(f"      • {loc_name}: {q['quantity']:,.2f}{reservado} - {lot_name}")
        
        print(f"\n   📦 STOCK TOTAL EN SISTEMA: {stock_info['total_quantity']:,.2f}")
        print(f"   🔒 Reservado: {stock_info['total_reserved']:,.2f}")
        print(f"   ✓ Disponible: {stock_info['disponible']:,.2f}")
        
        # 3. Calcular impacto
        print("\n[3/5] Calculando impacto del ajuste...")
        impacto = self.calcular_impacto(producto, stock_info['total_quantity'], qty_fisica)
        
        print(f"\n   ┌─────────────────────────────────────────────────┐")
        print(f"   │  RESUMEN DEL AJUSTE                             │")
        print(f"   ├─────────────────────────────────────────────────┤")
        print(f"   │  Stock en sistema:     {impacto['stock_sistema']:>15,.2f}      │")
        print(f"   │  Stock físico real:    {impacto['stock_fisico']:>15,.2f}      │")
        print(f"   │  ─────────────────────────────────────          │")
        print(f"   │  DIFERENCIA:           {impacto['diferencia']:>+15,.2f}      │")
        print(f"   │  Tipo de ajuste:       {impacto['tipo_ajuste']:>15}      │")
        print(f"   └─────────────────────────────────────────────────┘")
        
        if impacto['diferencia'] != 0:
            print(f"\n   💰 IMPACTO CONTABLE ESTIMADO:")
            print(f"      • Costo unitario: ${impacto['costo_unitario']:,.2f}")
            print(f"      • Valor del ajuste: ${impacto['impacto_valor']:+,.2f}")
            
            if impacto['diferencia'] < 0:
                print(f"\n   ⚠️ ALERTA: Se registrará una PÉRDIDA de ${impacto['impacto_valor_abs']:,.2f}")
                print(f"      El ajuste moverá {abs(impacto['diferencia']):,.2f} unidades a 'Inventory Loss'")
            else:
                print(f"\n   ✓ Se registrará una GANANCIA de ${impacto['impacto_valor_abs']:,.2f}")
                print(f"      El ajuste ingresará {impacto['diferencia']:,.2f} unidades desde 'Inventory Adjustment'")
        
        # 4. Verificar reservas pendientes
        print("\n[4/5] Verificando reservas y pickings pendientes...")
        pickings_pendientes = self.obtener_pickings_pendientes(producto['id'], stock_info['locations'])
        
        if pickings_pendientes:
            print(f"\n   ⚠️ ATENCIÓN: Hay {len(pickings_pendientes)} movimiento(s) pendiente(s):")
            for m in pickings_pendientes[:5]:
                picking_name = m['picking_id'][1] if m['picking_id'] else 'Sin picking'
                print(f"      • {picking_name}: {m['product_uom_qty']} uds [{m['state']}]")
            
            total_pendiente = sum(m['product_uom_qty'] for m in pickings_pendientes)
            print(f"\n   Total reservado/pendiente: {total_pendiente:,.2f} unidades")
            
            if qty_fisica < total_pendiente:
                print(f"\n   🔴 CONFLICTO: El stock físico ({qty_fisica}) es menor que las reservas ({total_pendiente})")
                print(f"       Se deberán liberar reservas o cancelar pickings antes del ajuste")
        else:
            print("   ✓ No hay reservas ni pickings pendientes")
        
        # 5. Movimientos recientes
        print("\n[5/5] Últimos movimientos (30 días)...")
        movimientos = self.obtener_movimientos_recientes(producto['id'], stock_info['locations'])
        
        if movimientos:
            print(f"\n   Últimos {len(movimientos)} movimientos:")
            entradas = 0
            salidas = 0
            for m in movimientos[:10]:
                fecha = m['date'][:10]
                picking = m['picking_id'][1] if m['picking_id'] else m.get('reference', 'N/A')
                origen = m.get('origin', '')
                
                # Determinar si es entrada o salida de RF/Insumos
                loc_from = m['location_id'][0] if m['location_id'] else 0
                loc_to = m['location_dest_id'][0] if m['location_dest_id'] else 0
                
                if loc_to in stock_info['locations']:
                    tipo = "→ ENTRADA"
                    entradas += m['quantity_done']
                else:
                    tipo = "← SALIDA "
                    salidas += m['quantity_done']
                
                print(f"      {fecha} | {tipo} | {m['quantity_done']:>10,.2f} | {picking[:30]}")
            
            print(f"\n   Resumen 30 días: Entradas: {entradas:,.2f} | Salidas: {salidas:,.2f} | Neto: {entradas-salidas:+,.2f}")
        else:
            print("   No hay movimientos en los últimos 30 días")
        
        # Resumen final
        print("\n" + "="*70)
        print("  RESUMEN FINAL - DRY RUN")
        print("="*70)
        
        if impacto['diferencia'] == 0:
            print("\n  ✅ NO SE REQUIERE AJUSTE - El stock físico coincide con el sistema")
        else:
            print(f"\n  📋 ACCIÓN REQUERIDA: {impacto['tipo_ajuste']} de {abs(impacto['diferencia']):,.2f} unidades")
            print(f"  💰 Impacto contable: ${impacto['impacto_valor']:+,.2f}")
            
            if stock_info['total_reserved'] > 0 and qty_fisica < stock_info['total_reserved']:
                print(f"\n  ⚠️ ADVERTENCIA: Hay reservas que superan el stock físico")
                print(f"     Liberar reservas antes de ajustar")
            
            print(f"\n  Para ejecutar este ajuste, ejecute:")
            print(f"  python ajuste_insumos_dryrun.py --code {default_code} --qty {qty_fisica} --execute")
        
        print("\n" + "="*70)
        
        return {
            'producto': producto,
            'stock_info': stock_info,
            'impacto': impacto,
            'pickings_pendientes': len(pickings_pendientes),
            'movimientos_recientes': len(movimientos)
        }
    
    def ejecutar_ajuste(self, default_code: str, qty_fisica: float, motivo: str = "Regularización conteo físico") -> bool:
        """Ejecuta el ajuste de inventario (SOLO con --execute)"""
        
        print("\n" + "="*70)
        print("  ⚡ EJECUTANDO AJUSTE DE INVENTARIO")
        print("="*70)
        
        # Buscar producto
        producto = self.buscar_producto(default_code)
        if not producto:
            print(f"❌ Producto no encontrado: {default_code}")
            return False
        
        # Obtener stock actual
        stock_info = self.obtener_stock_rf_insumos(producto['id'])
        stock_actual = stock_info['total_quantity']
        diferencia = qty_fisica - stock_actual
        
        if diferencia == 0:
            print("✓ No se requiere ajuste - stock ya coincide")
            return True
        
        print(f"\n  Producto: [{producto['default_code']}] {producto['name']}")
        print(f"  Stock sistema: {stock_actual:,.2f}")
        print(f"  Stock físico: {qty_fisica:,.2f}")
        print(f"  Diferencia: {diferencia:+,.2f}")
        
        # Crear ajuste de inventario
        try:
            # Buscar o crear el quant para ajustar
            quant_id = self.models.execute_kw(
                DB, self.uid, PASSWORD,
                'stock.quant', 'search',
                [[
                    ('product_id', '=', producto['id']),
                    ('location_id', '=', RF_INSUMOS_LOCATION_ID)
                ]],
                {'limit': 1}
            )
            
            if quant_id:
                # Actualizar quant existente usando el wizard
                print(f"\n  Actualizando quant ID {quant_id[0]}...")
                
                # Usar _apply_inventory para forzar la cantidad
                self.models.execute_kw(
                    DB, self.uid, PASSWORD,
                    'stock.quant', 'write',
                    [quant_id, {'inventory_quantity': qty_fisica}]
                )
                
                # Aplicar el ajuste
                self.models.execute_kw(
                    DB, self.uid, PASSWORD,
                    'stock.quant', 'action_apply_inventory',
                    [quant_id]
                )
                
                print(f"  ✓ Ajuste aplicado exitosamente")
                
            else:
                # Crear nuevo quant si no existe
                print(f"\n  No existe quant, creando nuevo con qty={qty_fisica}...")
                
                if qty_fisica > 0:
                    new_quant = self.models.execute_kw(
                        DB, self.uid, PASSWORD,
                        'stock.quant', 'create',
                        [{
                            'product_id': producto['id'],
                            'location_id': RF_INSUMOS_LOCATION_ID,
                            'inventory_quantity': qty_fisica,
                        }]
                    )
                    
                    # Aplicar
                    self.models.execute_kw(
                        DB, self.uid, PASSWORD,
                        'stock.quant', 'action_apply_inventory',
                        [[new_quant]]
                    )
                    
                    print(f"  ✓ Quant creado y ajuste aplicado (ID: {new_quant})")
                else:
                    print(f"  ⚠️ No se puede crear quant con cantidad negativa")
                    return False
            
            # Verificar resultado
            stock_nuevo = self.obtener_stock_rf_insumos(producto['id'])
            print(f"\n  📦 Stock después del ajuste: {stock_nuevo['total_quantity']:,.2f}")
            
            if abs(stock_nuevo['total_quantity'] - qty_fisica) < 0.01:
                print(f"  ✅ AJUSTE EXITOSO")
                return True
            else:
                print(f"  ⚠️ El stock no coincide exactamente. Revisar manualmente.")
                return False
                
        except Exception as e:
            print(f"\n  ❌ ERROR al ejecutar ajuste: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description='Ajuste de Insumos - Modo Dry Run',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python ajuste_insumos_dryrun.py --code 500000-24 --qty 1500
  python ajuste_insumos_dryrun.py --code 500058 --qty 5000 --execute
  
El modo dry run muestra toda la repercusión sin hacer cambios.
Use --execute para aplicar el ajuste realmente.
        """
    )
    
    parser.add_argument('--code', '-c', required=True, 
                       help='Código del producto (default_code)')
    parser.add_argument('--qty', '-q', type=float, required=True,
                       help='Cantidad física real contada')
    parser.add_argument('--execute', '-x', action='store_true',
                       help='Ejecutar el ajuste realmente (sin esto es solo dry run)')
    parser.add_argument('--motivo', '-m', default='Regularización conteo físico',
                       help='Motivo del ajuste')
    
    args = parser.parse_args()
    
    try:
        ajustador = AjusteInsumosDryRun()
        
        if args.execute:
            # Modo ejecución real
            print("\n" + "!"*70)
            print("  ⚠️  MODO EJECUCIÓN REAL - SE APLICARÁN CAMBIOS AL SISTEMA")
            print("!"*70)
            
            confirmacion = input("\n¿Está seguro de ejecutar el ajuste? (escriba 'SI' para confirmar): ")
            if confirmacion.upper() != 'SI':
                print("Operación cancelada")
                return
            
            resultado = ajustador.ejecutar_ajuste(args.code, args.qty, args.motivo)
            
        else:
            # Modo dry run (por defecto)
            resultado = ajustador.generar_reporte_dryrun(args.code, args.qty)
        
        # Guardar resultado
        if resultado:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"ajuste_dryrun_{args.code}_{timestamp}.json"
            
            # Serializar solo datos básicos
            if isinstance(resultado, dict):
                save_data = {
                    'codigo': args.code,
                    'qty_fisica': args.qty,
                    'timestamp': timestamp,
                    'producto_id': resultado.get('producto', {}).get('id'),
                    'producto_nombre': resultado.get('producto', {}).get('name'),
                    'stock_sistema': resultado.get('impacto', {}).get('stock_sistema'),
                    'diferencia': resultado.get('impacto', {}).get('diferencia'),
                    'impacto_valor': resultado.get('impacto', {}).get('impacto_valor'),
                    'ejecutado': args.execute
                }
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(save_data, f, indent=2, ensure_ascii=False)
                
                print(f"\n  📄 Resultado guardado en: {filename}")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
