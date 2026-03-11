#!/usr/bin/env python3
"""
AJUSTE BATCH DE INSUMOS - PROCESAR LISTA
=========================================
Procesa una lista de productos con sus cantidades físicas.

Entrada: Archivo CSV o entrada directa
Formato: codigo,cantidad

Uso:
    python ajuste_insumos_batch.py --file conteo.csv
    python ajuste_insumos_batch.py --interactive
"""

import xmlrpc.client
import argparse
import csv
from datetime import datetime
import json
import os

# Configuración Odoo
URL = "https://riofuturo.server98c6e.oerpondemand.net"
DB = "riofuturo-master"
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

# Ubicaciones RF/Insumos
RF_INSUMOS_LOCATION_ID = 24  # RF/Insumos/Bodega Insumos
RF_INSUMOS_PARENT_ID = 5474  # RF/Insumos (padre)


class AjusteBatchInsumos:
    def __init__(self):
        self.common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
        self.uid = self.common.authenticate(DB, USERNAME, PASSWORD, {})
        self.models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
        
        if not self.uid:
            raise Exception("Error de autenticación")
        
        # Cachear ubicaciones RF/Insumos
        self.locations = self.models.execute_kw(
            DB, self.uid, PASSWORD,
            'stock.location', 'search',
            [[('id', 'child_of', RF_INSUMOS_PARENT_ID), ('usage', '=', 'internal')]]
        )
        
        print(f"✓ Conectado a Odoo | {len(self.locations)} ubicaciones RF/Insumos")
    
    def buscar_producto(self, default_code: str) -> dict:
        """Busca producto por default_code"""
        products = self.models.execute_kw(
            DB, self.uid, PASSWORD,
            'product.product', 'search_read',
            [[('default_code', '=', default_code)]],
            {'fields': ['id', 'name', 'default_code', 'standard_price', 'uom_id']}
        )
        return products[0] if products else None
    
    def obtener_stock(self, product_id: int) -> dict:
        """Obtiene stock y quants del producto"""
        quants = self.models.execute_kw(
            DB, self.uid, PASSWORD,
            'stock.quant', 'search_read',
            [[('product_id', '=', product_id), ('location_id', 'in', self.locations)]],
            {'fields': ['location_id', 'quantity', 'reserved_quantity', 'lot_id']}
        )
        
        total_qty = sum(q['quantity'] for q in quants)
        total_reserved = sum(q['reserved_quantity'] for q in quants)
        num_lotes = len(set(q['lot_id'][0] for q in quants if q['lot_id']))
        
        return {
            'quants': quants,
            'total': total_qty,
            'reserved': total_reserved,
            'num_quants': len(quants),
            'num_lotes': num_lotes
        }
    
    def analizar_producto(self, codigo: str, qty_fisica: float) -> dict:
        """Analiza un producto y retorna resumen para el batch"""
        producto = self.buscar_producto(codigo)
        
        if not producto:
            return {
                'codigo': codigo,
                'qty_fisica': qty_fisica,
                'estado': 'ERROR',
                'mensaje': 'Producto no encontrado',
                'diferencia': None,
                'impacto_valor': None
            }
        
        stock = self.obtener_stock(producto['id'])
        diferencia = qty_fisica - stock['total']
        costo = producto.get('standard_price', 0)
        impacto = diferencia * costo
        
        # Determinar alertas
        alertas = []
        if stock['num_quants'] > 1:
            alertas.append(f"⚠️ {stock['num_quants']} quants")
        if stock['num_lotes'] > 1:
            alertas.append(f"⚠️ {stock['num_lotes']} lotes")
        if stock['reserved'] > 0:
            alertas.append(f"🔒 {stock['reserved']} reservado")
        
        return {
            'codigo': codigo,
            'producto_id': producto['id'],
            'nombre': producto['name'][:40],
            'udm': producto['uom_id'][1] if producto['uom_id'] else 'Un',
            'qty_fisica': qty_fisica,
            'stock_sistema': stock['total'],
            'diferencia': diferencia,
            'tipo': 'ENTRADA' if diferencia > 0 else 'SALIDA' if diferencia < 0 else 'OK',
            'costo_unitario': costo,
            'impacto_valor': impacto,
            'num_quants': stock['num_quants'],
            'num_lotes': stock['num_lotes'],
            'reservado': stock['reserved'],
            'alertas': ', '.join(alertas) if alertas else '',
            'estado': 'ANALIZADO'
        }
    
    def procesar_lista(self, items: list) -> list:
        """Procesa lista de (codigo, cantidad)"""
        resultados = []
        
        print(f"\n{'='*100}")
        print(f"  ANÁLISIS BATCH DE AJUSTES - {len(items)} productos")
        print(f"{'='*100}\n")
        
        for i, (codigo, qty) in enumerate(items, 1):
            print(f"  [{i}/{len(items)}] Analizando {codigo}...", end='')
            resultado = self.analizar_producto(codigo.strip(), float(qty))
            resultados.append(resultado)
            
            if resultado['estado'] == 'ERROR':
                print(f" ❌ {resultado['mensaje']}")
            else:
                print(f" ✓ Dif: {resultado['diferencia']:+,.2f} | ${resultado['impacto_valor']:+,.2f}")
        
        return resultados
    
    def generar_reporte(self, resultados: list) -> None:
        """Genera reporte consolidado"""
        
        # Separar por tipo
        encontrados = [r for r in resultados if r['estado'] == 'ANALIZADO']
        errores = [r for r in resultados if r['estado'] == 'ERROR']
        entradas = [r for r in encontrados if r['diferencia'] > 0]
        salidas = [r for r in encontrados if r['diferencia'] < 0]
        sin_cambio = [r for r in encontrados if r['diferencia'] == 0]
        
        print(f"\n{'='*100}")
        print(f"  RESUMEN DEL ANÁLISIS BATCH")
        print(f"{'='*100}")
        
        print(f"\n  Total productos analizados: {len(resultados)}")
        print(f"  ✓ Encontrados: {len(encontrados)}")
        print(f"  ❌ No encontrados: {len(errores)}")
        print(f"\n  Requieren ENTRADA: {len(entradas)}")
        print(f"  Requieren SALIDA: {len(salidas)}")
        print(f"  Sin cambio: {len(sin_cambio)}")
        
        # Impacto total
        total_entradas_qty = sum(r['diferencia'] for r in entradas)
        total_salidas_qty = sum(abs(r['diferencia']) for r in salidas)
        total_entradas_valor = sum(r['impacto_valor'] for r in entradas)
        total_salidas_valor = sum(abs(r['impacto_valor']) for r in salidas)
        
        print(f"\n  💰 IMPACTO CONTABLE TOTAL:")
        print(f"     Entradas: +{total_entradas_qty:,.2f} uds | ${total_entradas_valor:+,.2f}")
        print(f"     Salidas:  -{total_salidas_qty:,.2f} uds | ${-total_salidas_valor:,.2f}")
        print(f"     NETO:     ${total_entradas_valor - total_salidas_valor:+,.2f}")
        
        # Tabla detallada
        print(f"\n{'='*100}")
        print(f"  DETALLE DE AJUSTES REQUERIDOS")
        print(f"{'='*100}")
        print(f"  {'CÓDIGO':<15} {'PRODUCTO':<30} {'SISTEMA':>12} {'FÍSICO':>10} {'DIFERENCIA':>12} {'VALOR':>15} {'ALERTAS'}")
        print(f"  {'-'*15} {'-'*30} {'-'*12} {'-'*10} {'-'*12} {'-'*15} {'-'*20}")
        
        for r in sorted(encontrados, key=lambda x: x['impacto_valor']):
            if r['diferencia'] != 0:
                print(f"  {r['codigo']:<15} {r['nombre']:<30} {r['stock_sistema']:>12,.2f} {r['qty_fisica']:>10,.2f} {r['diferencia']:>+12,.2f} ${r['impacto_valor']:>14,.2f} {r['alertas']}")
        
        # Errores
        if errores:
            print(f"\n  ❌ PRODUCTOS NO ENCONTRADOS:")
            for e in errores:
                print(f"     {e['codigo']} - {e['mensaje']}")
        
        # Alertas
        con_alertas = [r for r in encontrados if r['alertas']]
        if con_alertas:
            print(f"\n  ⚠️ PRODUCTOS CON ALERTAS (revisar antes de ajustar):")
            for r in con_alertas:
                print(f"     {r['codigo']}: {r['alertas']}")
        
        print(f"\n{'='*100}")
    
    def exportar_csv(self, resultados: list, filename: str) -> None:
        """Exporta resultados a CSV"""
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'codigo', 'producto_id', 'nombre', 'udm', 'stock_sistema', 'qty_fisica', 
                'diferencia', 'tipo', 'costo_unitario', 'impacto_valor',
                'num_quants', 'num_lotes', 'reservado', 'alertas', 'estado'
            ], extrasaction='ignore')
            writer.writeheader()
            for r in resultados:
                if r['estado'] == 'ANALIZADO':
                    writer.writerow(r)
        
        print(f"\n  📄 Exportado a: {filename}")
    
    def modo_interactivo(self) -> list:
        """Modo interactivo para ingresar productos uno a uno"""
        items = []
        
        print("\n" + "="*70)
        print("  MODO INTERACTIVO")
        print("  Ingrese: codigo,cantidad (o 'fin' para terminar)")
        print("="*70 + "\n")
        
        while True:
            entrada = input("  > ").strip()
            
            if entrada.lower() in ['fin', 'end', 'q', 'quit', '']:
                break
            
            try:
                partes = entrada.replace(';', ',').split(',')
                if len(partes) >= 2:
                    codigo = partes[0].strip()
                    qty = float(partes[1].strip())
                    items.append((codigo, qty))
                    print(f"    ✓ Agregado: {codigo} -> {qty}")
                else:
                    print("    ❌ Formato inválido. Use: codigo,cantidad")
            except ValueError:
                print("    ❌ Cantidad inválida")
        
        return items


def main():
    parser = argparse.ArgumentParser(description='Ajuste Batch de Insumos')
    
    parser.add_argument('--file', '-f', 
                       help='Archivo CSV con productos (formato: codigo,cantidad)')
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Modo interactivo para ingresar productos')
    parser.add_argument('--output', '-o', 
                       help='Archivo de salida CSV (opcional)')
    
    args = parser.parse_args()
    
    try:
        batch = AjusteBatchInsumos()
        items = []
        
        if args.file:
            # Leer desde archivo
            if os.path.exists(args.file):
                with open(args.file, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if len(row) >= 2 and not row[0].startswith('#'):
                            try:
                                items.append((row[0].strip(), float(row[1].strip())))
                            except ValueError:
                                continue
                print(f"✓ Leídos {len(items)} productos desde {args.file}")
            else:
                print(f"❌ Archivo no encontrado: {args.file}")
                return
        
        elif args.interactive:
            items = batch.modo_interactivo()
        
        else:
            # Demo con algunos productos
            print("\n  Sin archivo ni modo interactivo. Usando productos de ejemplo...")
            items = [
                ('500000-24', 1500),
                ('500340', 5000),
                ('500058', 8000),
            ]
        
        if not items:
            print("No hay productos para analizar")
            return
        
        # Procesar
        resultados = batch.procesar_lista(items)
        
        # Reporte
        batch.generar_reporte(resultados)
        
        # Exportar
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = args.output or f"batch_ajustes_{timestamp}.csv"
        batch.exportar_csv(resultados, output_file)
        
        # Guardar JSON también
        json_file = output_file.replace('.csv', '.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(resultados, f, indent=2, ensure_ascii=False, default=str)
        print(f"  📄 JSON guardado en: {json_file}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
