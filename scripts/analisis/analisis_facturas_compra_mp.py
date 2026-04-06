#!/usr/bin/env python3
"""
ANÁLISIS DE FACTURAS DE COMPRA DE MATERIA PRIMA (MP)
====================================================
Período: Diciembre 2025 - Fecha actual
Datos extraídos: Proveedor, kg, contabilidad, OC relacionada, etc.
"""

import xmlrpc.client
from datetime import datetime
from collections import defaultdict
import csv
import json
import os

# Configuración Odoo
URL = "https://riofuturo.server98c6e.oerpondemand.net"
DB = "riofuturo-master"
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

# Período de análisis
FECHA_INICIO = "2025-12-01"
FECHA_FIN = datetime.now().strftime("%Y-%m-%d")

# Directorio de salida
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


class AnalisisFacturasMP:
    def __init__(self):
        print("=" * 100)
        print("ANÁLISIS DE FACTURAS DE COMPRA - MATERIA PRIMA (MP)")
        print(f"Período: {FECHA_INICIO} a {FECHA_FIN}")
        print("=" * 100)
        
        # Conectar a Odoo
        self.common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
        self.uid = self.common.authenticate(DB, USERNAME, PASSWORD, {})
        self.models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
        
        if not self.uid:
            raise Exception("Error de autenticación con Odoo")
        
        print(f"✓ Conectado a Odoo como UID: {self.uid}")
        
        # Cache de datos
        self.categorias_mp = []
        self.productos_mp = {}
        self.proveedores = {}
        self.cuentas_contables = {}
        self.ordenes_compra = {}
    
    def search_read(self, model, domain, fields, limit=0, order=None):
        """Wrapper para búsquedas en Odoo"""
        opts = {'fields': fields}
        if limit > 0:
            opts['limit'] = limit
        if order:
            opts['order'] = order
        return self.models.execute_kw(DB, self.uid, PASSWORD, model, 'search_read', [domain], opts)
    
    def cargar_categorias_mp(self):
        """Identifica las categorías de Materia Prima (MP)"""
        print("\n" + "=" * 80)
        print("1️⃣  IDENTIFICANDO CATEGORÍAS DE MATERIA PRIMA")
        print("=" * 80)
        
        # Buscar categorías que contengan MP, Materia Prima, Fruta, PSP
        patrones = ['MP', 'Materia Prima', 'Fruta', 'PSP', 'Cereza', 'Arándano', 'Ciruela', 'Durazno', 'Manzana']
        
        todas_categorias = self.search_read(
            'product.category', 
            [], 
            ['id', 'name', 'complete_name', 'parent_id']
        )
        
        print(f"\n📋 Total categorías en Odoo: {len(todas_categorias)}")
        
        # Filtrar categorías relevantes para MP
        for cat in todas_categorias:
            nombre = (cat.get('complete_name') or cat.get('name', '')).upper()
            for patron in patrones:
                if patron.upper() in nombre:
                    self.categorias_mp.append(cat)
                    break
        
        print(f"\n✅ Categorías identificadas como MP: {len(self.categorias_mp)}")
        for cat in self.categorias_mp:
            print(f"   [{cat['id']:5}] {cat.get('complete_name', cat['name'])}")
        
        return [c['id'] for c in self.categorias_mp]
    
    def cargar_productos_mp(self, categ_ids):
        """Carga productos de las categorías de MP"""
        print("\n" + "=" * 80)
        print("2️⃣  CARGANDO PRODUCTOS DE MATERIA PRIMA")
        print("=" * 80)
        
        if not categ_ids:
            print("⚠️  No se encontraron categorías - buscando por nombre de producto")
            # Buscar productos por nombre si no hay categorías
            productos = self.search_read(
                'product.product',
                ['|', '|', '|', '|',
                 ('name', 'ilike', 'cereza'),
                 ('name', 'ilike', 'arándano'),
                 ('name', 'ilike', 'ciruela'),
                 ('name', 'ilike', 'durazno'),
                 ('name', 'ilike', 'manzana')],
                ['id', 'name', 'default_code', 'categ_id', 'uom_id', 'standard_price']
            )
        else:
            productos = self.search_read(
                'product.product',
                [('categ_id', 'in', categ_ids)],
                ['id', 'name', 'default_code', 'categ_id', 'uom_id', 'standard_price']
            )
        
        for p in productos:
            self.productos_mp[p['id']] = p
        
        print(f"\n✅ Productos MP cargados: {len(self.productos_mp)}")
        
        # Mostrar ejemplos
        for i, (pid, p) in enumerate(list(self.productos_mp.items())[:10]):
            print(f"   [{pid:5}] {p.get('default_code', '-'):15} | {p['name'][:50]}")
        
        if len(self.productos_mp) > 10:
            print(f"   ... y {len(self.productos_mp) - 10} productos más")
        
        return list(self.productos_mp.keys())
    
    def obtener_facturas_compra(self):
        """Obtiene todas las facturas de compra (in_invoice) del período"""
        print("\n" + "=" * 80)
        print("3️⃣  OBTENIENDO FACTURAS DE COMPRA")
        print("=" * 80)
        
        domain = [
            ('move_type', '=', 'in_invoice'),
            ('state', '=', 'posted'),
            ('date', '>=', FECHA_INICIO),
            ('date', '<=', FECHA_FIN)
        ]
        
        facturas = self.search_read(
            'account.move',
            domain,
            [
                'id', 'name', 'ref', 'invoice_date', 'date', 
                'partner_id', 'amount_total', 'amount_untaxed', 'amount_tax',
                'state', 'payment_state', 'invoice_origin',
                'currency_id', 'company_id', 'journal_id',
                'invoice_line_ids', 'l10n_latam_document_number',
                'l10n_latam_document_type_id'
            ],
            order='date desc'
        )
        
        print(f"\n✅ Total facturas de compra en período: {len(facturas)}")
        
        return facturas
    
    def obtener_lineas_factura(self, factura_ids):
        """Obtiene las líneas de factura con detalle de productos"""
        print("\n" + "=" * 80)
        print("4️⃣  OBTENIENDO LÍNEAS DE FACTURA CON DETALLE")
        print("=" * 80)
        
        lineas = self.search_read(
            'account.move.line',
            [
                ('move_id', 'in', factura_ids),
                ('display_type', 'not in', ['line_section', 'line_note']),
                ('product_id', '!=', False)
            ],
            [
                'id', 'move_id', 'product_id', 'name', 'quantity', 'price_unit',
                'price_subtotal', 'price_total', 'discount',
                'account_id', 'tax_ids', 'analytic_distribution',
                'purchase_line_id', 'product_uom_id',
                'debit', 'credit', 'balance'
            ]
        )
        
        print(f"\n✅ Líneas de factura obtenidas: {len(lineas)}")
        
        return lineas
    
    def vincular_ordenes_compra(self, lineas):
        """Busca y vincula las órdenes de compra relacionadas"""
        print("\n" + "=" * 80)
        print("5️⃣  VINCULANDO ÓRDENES DE COMPRA")
        print("=" * 80)
        
        # Obtener IDs únicos de purchase_line_id
        purchase_line_ids = list(set(
            l['purchase_line_id'][0] 
            for l in lineas 
            if l.get('purchase_line_id')
        ))
        
        if not purchase_line_ids:
            print("⚠️  No hay líneas vinculadas a órdenes de compra")
            return {}
        
        print(f"🔗 Líneas de OC a buscar: {len(purchase_line_ids)}")
        
        # Obtener líneas de OC
        purchase_lines = self.search_read(
            'purchase.order.line',
            [('id', 'in', purchase_line_ids)],
            ['id', 'order_id', 'product_qty', 'price_unit', 'product_uom']
        )
        
        # Extraer IDs de órdenes únicas
        order_ids = list(set(pl['order_id'][0] for pl in purchase_lines if pl.get('order_id')))
        
        # Obtener órdenes de compra
        ordenes = self.search_read(
            'purchase.order',
            [('id', 'in', order_ids)],
            ['id', 'name', 'date_order', 'partner_id', 'state', 'amount_total']
        )
        
        for oc in ordenes:
            self.ordenes_compra[oc['id']] = oc
        
        # Crear mapeo línea -> orden
        linea_to_orden = {}
        for pl in purchase_lines:
            if pl.get('order_id'):
                linea_to_orden[pl['id']] = pl['order_id'][0]
        
        print(f"✅ Órdenes de compra encontradas: {len(self.ordenes_compra)}")
        
        return linea_to_orden
    
    def filtrar_lineas_mp(self, lineas, producto_ids):
        """Filtra solo las líneas que corresponden a productos de MP"""
        print("\n" + "=" * 80)
        print("6️⃣  FILTRANDO LÍNEAS DE MATERIA PRIMA")
        print("=" * 80)
        
        lineas_mp = []
        for l in lineas:
            if l.get('product_id'):
                product_id = l['product_id'][0]
                if product_id in producto_ids:
                    lineas_mp.append(l)
        
        print(f"✅ Líneas de MP encontradas: {len(lineas_mp)} de {len(lineas)} totales")
        
        return lineas_mp
    
    def cargar_datos_auxiliares(self, lineas, facturas):
        """Carga datos auxiliares: proveedores, cuentas contables"""
        print("\n" + "=" * 80)
        print("7️⃣  CARGANDO DATOS AUXILIARES")
        print("=" * 80)
        
        # Proveedores únicos
        partner_ids = list(set(f['partner_id'][0] for f in facturas if f.get('partner_id')))
        if partner_ids:
            partners = self.search_read(
                'res.partner',
                [('id', 'in', partner_ids)],
                ['id', 'name', 'vat', 'ref', 'city', 'country_id', 'phone', 'email']
            )
            for p in partners:
                self.proveedores[p['id']] = p
            print(f"✅ Proveedores cargados: {len(self.proveedores)}")
        
        # Cuentas contables únicas
        account_ids = list(set(l['account_id'][0] for l in lineas if l.get('account_id')))
        if account_ids:
            cuentas = self.search_read(
                'account.account',
                [('id', 'in', account_ids)],
                ['id', 'code', 'name', 'account_type']
            )
            for c in cuentas:
                self.cuentas_contables[c['id']] = c
            print(f"✅ Cuentas contables cargadas: {len(self.cuentas_contables)}")
    
    def generar_reporte(self, facturas, lineas_mp, linea_to_orden):
        """Genera el reporte consolidado"""
        print("\n" + "=" * 80)
        print("8️⃣  GENERANDO REPORTE CONSOLIDADO")
        print("=" * 80)
        
        # Crear diccionario de facturas por ID
        facturas_dict = {f['id']: f for f in facturas}
        
        # Construir datos del reporte
        reporte = []
        
        for linea in lineas_mp:
            factura = facturas_dict.get(linea['move_id'][0], {})
            producto = self.productos_mp.get(linea['product_id'][0], {})
            proveedor = self.proveedores.get(factura.get('partner_id', [None])[0], {}) if factura.get('partner_id') else {}
            cuenta = self.cuentas_contables.get(linea.get('account_id', [None])[0], {}) if linea.get('account_id') else {}
            
            # Buscar OC relacionada
            oc = {}
            if linea.get('purchase_line_id'):
                oc_id = linea_to_orden.get(linea['purchase_line_id'][0])
                if oc_id:
                    oc = self.ordenes_compra.get(oc_id, {})
            
            row = {
                # Factura
                'factura_id': factura.get('id', ''),
                'factura_numero': factura.get('name', ''),
                'factura_ref': factura.get('ref', ''),
                'factura_fecha': factura.get('invoice_date', ''),
                'factura_fecha_contable': factura.get('date', ''),
                'factura_total': factura.get('amount_total', 0),
                'factura_subtotal': factura.get('amount_untaxed', 0),
                'factura_iva': factura.get('amount_tax', 0),
                'factura_estado_pago': factura.get('payment_state', ''),
                'documento_tipo': factura.get('l10n_latam_document_type_id', ['', ''])[1] if factura.get('l10n_latam_document_type_id') else '',
                'documento_numero': factura.get('l10n_latam_document_number', ''),
                
                # Proveedor
                'proveedor_id': proveedor.get('id', ''),
                'proveedor_nombre': proveedor.get('name', ''),
                'proveedor_rut': proveedor.get('vat', ''),
                'proveedor_ciudad': proveedor.get('city', ''),
                'proveedor_email': proveedor.get('email', ''),
                'proveedor_telefono': proveedor.get('phone', ''),
                
                # Producto (Línea)
                'producto_id': producto.get('id', ''),
                'producto_codigo': producto.get('default_code', ''),
                'producto_nombre': producto.get('name', ''),
                'producto_categoria': producto.get('categ_id', ['', ''])[1] if producto.get('categ_id') else '',
                'linea_descripcion': linea.get('name', ''),
                'cantidad': linea.get('quantity', 0),
                'precio_unitario': linea.get('price_unit', 0),
                'descuento_pct': linea.get('discount', 0),
                'subtotal': linea.get('price_subtotal', 0),
                'total': linea.get('price_total', 0),
                'uom': linea.get('product_uom_id', ['', ''])[1] if linea.get('product_uom_id') else '',
                
                # Contabilidad
                'cuenta_codigo': cuenta.get('code', ''),
                'cuenta_nombre': cuenta.get('name', ''),
                'cuenta_tipo': cuenta.get('account_type', ''),
                'debe': linea.get('debit', 0),
                'haber': linea.get('credit', 0),
                'analytic_distribution': json.dumps(linea.get('analytic_distribution', {})) if linea.get('analytic_distribution') else '',
                
                # Orden de Compra
                'oc_id': oc.get('id', ''),
                'oc_numero': oc.get('name', ''),
                'oc_fecha': oc.get('date_order', ''),
            }
            
            reporte.append(row)
        
        print(f"✅ Registros en reporte: {len(reporte)}")
        
        return reporte
    
    def calcular_estadisticas(self, reporte):
        """Calcula estadísticas del reporte"""
        print("\n" + "=" * 80)
        print("📊 ESTADÍSTICAS DEL ANÁLISIS")
        print("=" * 80)
        
        if not reporte:
            print("⚠️  No hay datos para calcular estadísticas")
            return
        
        # Total general
        total_subtotal = sum(r['subtotal'] for r in reporte)
        total_iva = sum(r.get('factura_iva', 0) for r in reporte)
        total_kg = sum(r['cantidad'] for r in reporte if 'kg' in str(r.get('uom', '')).lower() or 'kilo' in str(r.get('uom', '')).lower())
        
        print(f"\n💰 TOTALES:")
        print(f"   Subtotal (s/IVA):  ${total_subtotal:,.0f}")
        print(f"   Total kg:          {total_kg:,.2f} kg")
        
        # Por proveedor
        por_proveedor = defaultdict(lambda: {'subtotal': 0, 'cantidad': 0, 'facturas': set()})
        for r in reporte:
            prov = r['proveedor_nombre'] or 'Sin proveedor'
            por_proveedor[prov]['subtotal'] += r['subtotal']
            por_proveedor[prov]['cantidad'] += r['cantidad']
            por_proveedor[prov]['facturas'].add(r['factura_numero'])
        
        print(f"\n📋 POR PROVEEDOR (Top 10):")
        top_provs = sorted(por_proveedor.items(), key=lambda x: -x[1]['subtotal'])[:10]
        for prov, data in top_provs:
            print(f"   {prov[:40]:40} | ${data['subtotal']:>15,.0f} | {data['cantidad']:>12,.2f} | {len(data['facturas'])} facturas")
        
        # Por producto
        por_producto = defaultdict(lambda: {'subtotal': 0, 'cantidad': 0})
        for r in reporte:
            prod = r['producto_nombre'] or 'Sin producto'
            por_producto[prod]['subtotal'] += r['subtotal']
            por_producto[prod]['cantidad'] += r['cantidad']
        
        print(f"\n📦 POR PRODUCTO (Top 10):")
        top_prods = sorted(por_producto.items(), key=lambda x: -x[1]['subtotal'])[:10]
        for prod, data in top_prods:
            print(f"   {prod[:45]:45} | ${data['subtotal']:>15,.0f} | {data['cantidad']:>12,.2f}")
        
        # Por mes
        por_mes = defaultdict(lambda: {'subtotal': 0, 'cantidad': 0, 'facturas': 0})
        for r in reporte:
            fecha = r['factura_fecha'] or r['factura_fecha_contable']
            if fecha:
                mes = fecha[:7]  # YYYY-MM
                por_mes[mes]['subtotal'] += r['subtotal']
                por_mes[mes]['cantidad'] += r['cantidad']
                por_mes[mes]['facturas'] += 1
        
        print(f"\n📅 POR MES:")
        for mes in sorted(por_mes.keys()):
            data = por_mes[mes]
            print(f"   {mes} | ${data['subtotal']:>15,.0f} | {data['cantidad']:>12,.2f} | {data['facturas']} líneas")
        
        # Por cuenta contable
        por_cuenta = defaultdict(lambda: {'subtotal': 0, 'cantidad': 0})
        for r in reporte:
            cuenta = f"{r['cuenta_codigo']} - {r['cuenta_nombre']}" if r['cuenta_codigo'] else 'Sin cuenta'
            por_cuenta[cuenta]['subtotal'] += r['subtotal']
            por_cuenta[cuenta]['cantidad'] += r['cantidad']
        
        print(f"\n📚 POR CUENTA CONTABLE (Top 10):")
        top_cuentas = sorted(por_cuenta.items(), key=lambda x: -x[1]['subtotal'])[:10]
        for cuenta, data in top_cuentas:
            print(f"   {cuenta[:50]:50} | ${data['subtotal']:>15,.0f}")
    
    def exportar_csv(self, reporte, filename="facturas_compra_mp"):
        """Exporta el reporte a CSV"""
        if not reporte:
            print("⚠️  No hay datos para exportar")
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(OUTPUT_DIR, f"{filename}_{timestamp}.csv")
        
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=reporte[0].keys(), delimiter=';')
            writer.writeheader()
            writer.writerows(reporte)
        
        print(f"\n💾 CSV exportado: {filepath}")
        return filepath
    
    def exportar_json(self, reporte, filename="facturas_compra_mp"):
        """Exporta el reporte a JSON"""
        if not reporte:
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(OUTPUT_DIR, f"{filename}_{timestamp}.json")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(reporte, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"💾 JSON exportado: {filepath}")
        return filepath
    
    def ejecutar(self):
        """Ejecuta el análisis completo"""
        try:
            # 1. Cargar categorías de MP
            categ_ids = self.cargar_categorias_mp()
            
            # 2. Cargar productos de MP
            producto_ids = self.cargar_productos_mp(categ_ids)
            
            # 3. Obtener facturas de compra
            facturas = self.obtener_facturas_compra()
            
            if not facturas:
                print("\n⚠️  No se encontraron facturas en el período")
                return
            
            factura_ids = [f['id'] for f in facturas]
            
            # 4. Obtener líneas de factura
            lineas = self.obtener_lineas_factura(factura_ids)
            
            # 5. Vincular órdenes de compra
            linea_to_orden = self.vincular_ordenes_compra(lineas)
            
            # 6. Filtrar líneas de MP
            if producto_ids:
                lineas_mp = self.filtrar_lineas_mp(lineas, producto_ids)
            else:
                print("\n⚠️  No se encontraron productos MP específicos - usando todas las líneas")
                lineas_mp = lineas
            
            # 7. Cargar datos auxiliares
            self.cargar_datos_auxiliares(lineas_mp, facturas)
            
            # 8. Generar reporte
            reporte = self.generar_reporte(facturas, lineas_mp, linea_to_orden)
            
            # 9. Calcular estadísticas
            self.calcular_estadisticas(reporte)
            
            # 10. Exportar
            self.exportar_csv(reporte)
            self.exportar_json(reporte)
            
            print("\n" + "=" * 100)
            print("✅ ANÁLISIS COMPLETADO EXITOSAMENTE")
            print("=" * 100)
            
            return reporte
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return None


if __name__ == "__main__":
    analisis = AnalisisFacturasMP()
    analisis.ejecutar()
