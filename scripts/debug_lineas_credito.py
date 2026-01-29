"""
DEBUG: Analizar líneas de crédito y detectar montos absurdos
Objetivo: Identificar qué tipo de documentos están generando montos incorrectos
y cuándo debe o no cubrirse la línea de crédito.

LÓGICA CORREGIDA:
- Uso = Facturas no pagadas + Recepciones sin facturar (desde purchase.order.line)
- OCs tentativas son solo informativas, NO afectan el uso

PROBLEMA IDENTIFICADO Y CORREGIDO:
❌ ANTES: Se contaban recepciones (purchase.order.line) Y pickings done (stock.move)
   Esto causaba DUPLICACIÓN porque qty_received de las líneas PO ya incluye los pickings done
   Resultado: Porcentajes absurdos como 180036%, 431%, etc.

✅ AHORA: Solo se cuentan recepciones desde purchase.order.line (qty_received - qty_invoiced)
   Esto ya incluye TODAS las recepciones físicas realizadas
   Los pickings done NO se cuentan porque ya están reflejados en qty_received

NOTAS ADICIONALES:
- price_unit en stock.move puede ser 0 o incorrecto (otra razón para no usarlos)
- Conversión USD a CLP se hace para todos los montos en dólares
"""
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

# Función para obtener tipo de cambio USD
def get_usd_rate(odoo):
    """Obtiene tipo de cambio USD a CLP desde Odoo."""
    try:
        rates = odoo.search_read(
            'res.currency.rate',
            [['currency_id.name', '=', 'USD']],
            ['rate', 'name'],
            limit=1,
            order='name desc'
        )
        if rates and rates[0].get('rate'):
            return 1 / rates[0]['rate']
    except:
        pass
    return 950.0  # Fallback

def convert_usd_to_clp(amount, rate):
    """Convierte USD a CLP."""
    return amount * rate

# Configuración
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("=" * 140)
print("DEBUG: ANÁLISIS DE LÍNEAS DE CRÉDITO")
print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 140)

try:
    odoo = OdooClient(username=USERNAME, password=PASSWORD)
    print("✅ Conexión a Odoo establecida")
except Exception as e:
    print(f"❌ Error al conectar a Odoo: {e}")
    print("Verifica las credenciales y la conexión de red.")
    sys.exit(1)

# === 1. IDENTIFICAR PROVEEDORES CON LÍNEA DE CRÉDITO ===
print("\n📋 PROVEEDORES CON LÍNEA DE CRÉDITO ACTIVA:")
print("-" * 140)

partners = odoo.search_read(
    'res.partner',
    [['x_studio_linea_credito_activa', '=', True]],
    ['id', 'name', 'x_studio_linea_credito_monto', 'currency_id'],
    limit=200
)

print(f"{'ID':<8} {'Proveedor':<50} {'Línea Crédito':>18} {'Moneda':<10}")
print("-" * 140)
for p in sorted(partners, key=lambda x: float(x.get('x_studio_linea_credito_monto') or 0), reverse=True):
    currency = p.get('currency_id')
    currency_name = currency[1] if isinstance(currency, (list, tuple)) else ''
    linea = float(p.get('x_studio_linea_credito_monto') or 0)
    print(f"{p['id']:<8} {p['name'][:48]:<50} {linea:>18,.0f} {currency_name:<10}")

partner_ids = [p['id'] for p in partners]

# === 2. ANALIZAR FUENTES DE DATOS POR PARTNER ===
print("\n\n" + "=" * 140)
print("ANÁLISIS DETALLADO POR PROVEEDOR")
print("=" * 140)

# Tipo de cambio
usd_rate = get_usd_rate(odoo)
print(f"\n💱 Tipo de cambio USD: ${usd_rate:,.2f} CLP")

# Fecha desde (para filtrar temporada actual)
FECHA_DESDE = "2025-11-20"
print(f"📅 Fecha desde: {FECHA_DESDE}\n")

for p in partners[:5]:  # Analizar primeros 5 para debug
    pid = p['id']
    pname = p['name']
    linea_monto = float(p.get('x_studio_linea_credito_monto') or 0)
    
    print(f"\n{'='*80}")
    print(f"🏢 {pname} (ID: {pid})")
    print(f"   Línea de Crédito: ${linea_monto:,.0f}")
    print(f"{'='*80}")
    
    # === 2A. FACTURAS NO PAGADAS ===
    facturas = odoo.search_read(
        'account.move',
        [
            ['partner_id', '=', pid],
            ['move_type', '=', 'in_invoice'],
            ['state', '=', 'posted'],
            ['amount_residual', '>', 0],
            ['invoice_date', '>=', FECHA_DESDE]
        ],
        ['id', 'name', 'amount_total', 'amount_residual', 'invoice_date', 'currency_id', 'invoice_origin'],
        limit=100
    )
    
    total_facturas = 0
    print(f"\n📄 FACTURAS NO PAGADAS ({len(facturas)}):")
    if facturas:
        print(f"   {'Factura':<20} {'Fecha':<12} {'Total':>15} {'Residual':>15} {'Moneda':<8} {'Origen':<30}")
        print(f"   {'-'*100}")
        for f in facturas:
            currency = f.get('currency_id')
            currency_name = currency[1] if isinstance(currency, (list, tuple)) else 'CLP'
            residual = float(f.get('amount_residual') or 0)
            
            # Convertir a CLP si USD
            is_usd = 'USD' in currency_name.upper() if currency_name else False
            residual_clp = convert_usd_to_clp(residual, usd_rate) if is_usd else residual
            total_facturas += residual_clp
            
            print(f"   {f['name']:<20} {str(f.get('invoice_date') or '')[:10]:<12} "
                  f"{f.get('amount_total', 0):>15,.0f} {residual:>15,.0f} {currency_name:<8} "
                  f"{(f.get('invoice_origin') or '')[:28]:<30}")
    else:
        print("   Sin facturas pendientes")
    
    print(f"   → TOTAL FACTURAS (CLP): ${total_facturas:,.0f}")
    
    # === 2B. OCs DEL PROVEEDOR ===
    ocs = odoo.search_read(
        'purchase.order',
        [
            ['partner_id', '=', pid],
            ['state', 'not in', ['cancel']],
            ['date_order', '>=', FECHA_DESDE]
        ],
        ['id', 'name', 'amount_total', 'date_order', 'invoice_ids', 'currency_id', 'state'],
        limit=100
    )
    
    print(f"\n📋 ÓRDENES DE COMPRA ({len(ocs)}):")
    if ocs:
        print(f"   {'OC':<18} {'Fecha':<12} {'Estado':<12} {'Monto':>15} {'Moneda':<8} {'Facturas':<10}")
        print(f"   {'-'*85}")
        for oc in ocs:
            currency = oc.get('currency_id')
            currency_name = currency[1] if isinstance(currency, (list, tuple)) else 'CLP'
            invoice_ids = oc.get('invoice_ids') or []
            n_facturas = len(invoice_ids) if invoice_ids else 0
            print(f"   {oc['name']:<18} {str(oc.get('date_order') or '')[:10]:<12} "
                  f"{oc.get('state', ''):<12} {oc.get('amount_total', 0):>15,.0f} "
                  f"{currency_name:<8} {n_facturas:<10}")
    else:
        print("   Sin órdenes de compra")
    
    oc_ids = [oc['id'] for oc in ocs]
    
    # === 2C. LÍNEAS DE PO - RECEPCIONES SIN FACTURAR ===
    print(f"\n📦 RECEPCIONES SIN FACTURAR (via purchase.order.line):")
    
    total_recepciones = 0
    if oc_ids:
        po_lines = odoo.search_read(
            'purchase.order.line',
            [['order_id', 'in', oc_ids]],
            ['id', 'order_id', 'product_id', 'name', 'qty_received', 'qty_invoiced', 'price_unit'],
            limit=500
        )
        
        lineas_pendientes = []
        for line in po_lines:
            qty_received = float(line.get('qty_received') or 0)
            qty_invoiced = float(line.get('qty_invoiced') or 0)
            qty_pendiente = qty_received - qty_invoiced
            
            if qty_pendiente > 0:
                price_unit = float(line.get('price_unit') or 0)
                monto = qty_pendiente * price_unit
                order = line.get('order_id')
                order_name = order[1] if isinstance(order, (list, tuple)) else str(order)
                product = line.get('product_id')
                product_name = product[1][:40] if isinstance(product, (list, tuple)) else ''
                
                lineas_pendientes.append({
                    'order': order_name,
                    'product': product_name,
                    'qty_received': qty_received,
                    'qty_invoiced': qty_invoiced,
                    'qty_pendiente': qty_pendiente,
                    'price_unit': price_unit,
                    'monto': monto
                })
                total_recepciones += monto
        
        if lineas_pendientes:
            print(f"   {'OC':<18} {'Producto':<40} {'Recib.':>8} {'Fact.':>8} {'Pend.':>8} {'P.Unit':>10} {'Monto':>15}")
            print(f"   {'-'*115}")
            for l in lineas_pendientes[:15]:  # Mostrar primeras 15
                print(f"   {l['order']:<18} {l['product'][:38]:<40} "
                      f"{l['qty_received']:>8.0f} {l['qty_invoiced']:>8.0f} {l['qty_pendiente']:>8.0f} "
                      f"{l['price_unit']:>10,.0f} {l['monto']:>15,.0f}")
            if len(lineas_pendientes) > 15:
                print(f"   ... y {len(lineas_pendientes) - 15} líneas más")
        else:
            print("   Sin recepciones pendientes de facturar")
    else:
        print("   Sin OCs para analizar")
    
    print(f"   → TOTAL RECEPCIONES SIN FACTURAR: ${total_recepciones:,.0f}")
    
    # === 2D. PICKINGS DONE (stock.move) ===
    print(f"\n🚚 PICKINGS DONE (stock.move):")
    
    total_pickings = 0
    if oc_ids:
        pickings = odoo.search_read(
            'stock.picking',
            [
                ['purchase_id', 'in', oc_ids],
                ['state', '=', 'done'],
                ['picking_type_code', '=', 'incoming']
            ],
            ['id', 'name', 'purchase_id', 'scheduled_date'],
            limit=200
        )
        
        if pickings:
            picking_ids = [pk['id'] for pk in pickings]
            picking_map = {pk['id']: pk for pk in pickings}
            
            moves = odoo.search_read(
                'stock.move',
                [['picking_id', 'in', picking_ids]],
                ['id', 'picking_id', 'product_id', 'quantity_done', 'price_unit', 'purchase_line_id'],
                limit=1000
            )
            
            moves_con_valor = []
            for m in moves:
                qty_done = float(m.get('quantity_done') or 0)
                price_unit = float(m.get('price_unit') or 0)
                
                if qty_done > 0:
                    monto = qty_done * price_unit
                    picking = m.get('picking_id')
                    picking_id = picking[0] if isinstance(picking, (list, tuple)) else picking
                    picking_name = picking_map.get(picking_id, {}).get('name', '')
                    
                    product = m.get('product_id')
                    product_name = product[1][:40] if isinstance(product, (list, tuple)) else ''
                    
                    moves_con_valor.append({
                        'picking': picking_name,
                        'product': product_name,
                        'qty_done': qty_done,
                        'price_unit': price_unit,
                        'monto': monto,
                        'has_po_line': m.get('purchase_line_id') is not None
                    })
                    total_pickings += monto
            
            if moves_con_valor:
                print(f"   {'Picking':<20} {'Producto':<40} {'Cant.':>10} {'P.Unit':>12} {'Monto':>15} {'PO Line':<8}")
                print(f"   {'-'*115}")
                for mv in moves_con_valor[:15]:
                    po_line_indicator = "✓" if mv['has_po_line'] else "❌"
                    print(f"   {mv['picking']:<20} {mv['product'][:38]:<40} "
                          f"{mv['qty_done']:>10,.0f} {mv['price_unit']:>12,.0f} {mv['monto']:>15,.0f} {po_line_indicator:<8}")
                if len(moves_con_valor) > 15:
                    print(f"   ... y {len(moves_con_valor) - 15} moves más")
            else:
                print("   Sin moves con cantidad done > 0")
        else:
            print("   Sin pickings done")
    else:
        print("   Sin OCs para analizar")
    
    print(f"   → TOTAL PICKINGS DONE: ${total_pickings:,.0f}")
    
    # === RESUMEN ===
    print(f"\n📊 RESUMEN PROVEEDOR:")
    print(f"   {'Línea de Crédito:':<30} ${linea_monto:>18,.0f}")
    print(f"   {'Facturas no pagadas:':<30} ${total_facturas:>18,.0f}")
    print(f"   {'Recepciones sin facturar:':<30} ${total_recepciones:>18,.0f}")
    print(f"   {'Pickings done:':<30} ${total_pickings:>18,.0f}")
    print(f"   {'-'*50}")
    
    # POTENCIAL DOBLE CONTEO
    total_actual = total_facturas + total_recepciones + total_pickings
    print(f"   {'TOTAL ACTUAL (suma):':<30} ${total_actual:>18,.0f}")
    
    # Si hay recepción y picking, probablemente hay doble conteo
    if total_recepciones > 0 and total_pickings > 0:
        print(f"\n   ⚠️  ALERTA: Posible DOBLE CONTEO entre recepciones y pickings!")
        print(f"       Las recepciones (po.line) y pickings (stock.move) pueden ser lo mismo.")
        print(f"       Sugerencia: Usar SOLO recepciones (purchase.order.line) para evitar duplicación.")
        total_corregido = total_facturas + total_recepciones
        print(f"   {'TOTAL CORREGIDO (sin pickings):':<30} ${total_corregido:>18,.0f}")
        
        if linea_monto > 0:
            pct_actual = (total_actual / linea_monto * 100)
            pct_corregido = (total_corregido / linea_monto * 100)
            print(f"\n   {'% Uso (actual):':<30} {pct_actual:>18.1f}%")
            print(f"   {'% Uso (corregido):':<30} {pct_corregido:>18.1f}%")
    
    if linea_monto > 0 and total_actual > linea_monto * 2:
        print(f"\n   🔴 MONTO ABSURDO: Uso > 200% de la línea!")

# === 3. ANÁLISIS DE PRICE_UNIT EN STOCK.MOVE ===
print("\n\n" + "=" * 140)
print("ANÁLISIS DE PRICE_UNIT EN STOCK.MOVE")
print("=" * 140)
print("Verificando si price_unit está poblado correctamente en los moves...")

# Obtener muestra de moves recientes
sample_moves = odoo.search_read(
    'stock.move',
    [
        ['state', '=', 'done'],
        ['picking_type_id.code', '=', 'incoming'],
        ['date', '>=', FECHA_DESDE]
    ],
    ['id', 'name', 'product_id', 'quantity_done', 'price_unit', 'purchase_line_id'],
    limit=50,
    order='date desc'
)

moves_sin_precio = 0
moves_con_precio = 0
for m in sample_moves:
    price = float(m.get('price_unit') or 0)
    if price == 0:
        moves_sin_precio += 1
    else:
        moves_con_precio += 1

print(f"\nMuestra de {len(sample_moves)} moves recientes:")
print(f"   Con price_unit > 0: {moves_con_precio}")
print(f"   Con price_unit = 0: {moves_sin_precio}")

if moves_sin_precio > moves_con_precio:
    print(f"\n   ⚠️  ALERTA: La mayoría de moves NO tienen price_unit!")
    print(f"       Los pickings done no son confiables para calcular valores.")
    print(f"       RECOMENDACIÓN: Usar SOLO purchase.order.line para recepciones.")

print("\n" + "=" * 140)
print("DEBUG COMPLETADO")
print("=" * 140)
print("""
CONCLUSIONES Y RECOMENDACIONES:
===============================
1. Si hay doble conteo (recepciones + pickings), usar SOLO purchase.order.line
2. Si price_unit en stock.move es 0, no usar pickings para valores
3. Asegurar filtro de fecha_desde en TODOS los queries
4. Revisar conversión USD/CLP para partners con moneda USD
""")
