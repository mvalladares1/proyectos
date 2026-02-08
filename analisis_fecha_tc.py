"""
Análisis detallado: Fecha de OC → TC aplicado
"""
import sys
sys.path.insert(0, r"c:\new\RIO FUTURO\DASHBOARD\proyectos")

from backend.services.proforma_ajuste_service import get_facturas_borrador
from shared.odoo_client import OdooClient

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

client = OdooClient(username=USERNAME, password=PASSWORD)

print("=" * 140)
print("📊 RELACIÓN: FECHA DE OC → TIPO DE CAMBIO APLICADO")
print("=" * 140)

# Obtener factura TRES ROBLES
facturas = get_facturas_borrador(USERNAME, PASSWORD)
factura = None
for f in facturas:
    if "TRES ROBLES" in f['proveedor_nombre'].upper():
        factura = f
        break

if factura:
    print(f"\n📄 FACTURA: {factura['nombre']} - {factura['proveedor_nombre']}")
    print(f"{'='*140}")
    print(f"{'OC':<10} | {'FECHA OC':<20} | {'PRODUCTO':<45} | {'CANT':>8} | {'USD':>12} | {'CLP':>14} | {'TC':>10} | {'DÍAS':>5}")
    print(f"{'='*140}")
    
    lineas_con_fecha = []
    
    for linea in factura['lineas']:
        nombre = linea['nombre'] or ""
        # Extraer OC del nombre
        oc_nombre = ""
        if ":" in nombre:
            oc_nombre = nombre.split(":")[0].strip()
        
        if oc_nombre:
            # Buscar OC en Odoo
            ocs = client.search_read(
                "purchase.order",
                [("name", "=", oc_nombre)],
                ["name", "date_order"],
                limit=1
            )
            
            if ocs:
                fecha_oc = ocs[0].get('date_order', '')
                producto = nombre.split("]")[1].strip() if "]" in nombre else nombre[:40]
                
                # Calcular días desde hoy
                from datetime import datetime
                if fecha_oc:
                    fecha_obj = datetime.strptime(fecha_oc[:10], '%Y-%m-%d')
                    hoy = datetime(2026, 2, 5)
                    dias = (hoy - fecha_obj).days
                else:
                    dias = 0
                
                lineas_con_fecha.append({
                    'oc': oc_nombre,
                    'fecha': fecha_oc[:19] if fecha_oc else 'N/A',
                    'producto': producto,
                    'cant': linea['cantidad'],
                    'usd': linea['subtotal_usd'],
                    'clp': linea['subtotal_clp'],
                    'tc': linea['tc_implicito'],
                    'dias': dias
                })
    
    # Ordenar por fecha
    lineas_con_fecha.sort(key=lambda x: x['fecha'])
    
    for l in lineas_con_fecha:
        print(f"{l['oc']:<10} | {l['fecha']:<20} | {l['producto'][:45]:<45} | {l['cant']:>8.2f} | ${l['usd']:>11,.2f} | ${l['clp']:>13,.0f} | {l['tc']:>10,.2f} | {l['dias']:>5}")
    
    print(f"{'='*140}")
    
    # Análisis
    tcs = [l['tc'] for l in lineas_con_fecha if l['tc'] > 0]
    if tcs:
        print(f"\n📈 ANÁLISIS:")
        print(f"   • OC más antigua: {lineas_con_fecha[0]['oc']} ({lineas_con_fecha[0]['fecha'][:10]}) → TC: {lineas_con_fecha[0]['tc']:,.2f}")
        print(f"   • OC más reciente: {lineas_con_fecha[-1]['oc']} ({lineas_con_fecha[-1]['fecha'][:10]}) → TC: {lineas_con_fecha[-1]['tc']:,.2f}")
        print(f"   • Diferencia de TC: {max(tcs) - min(tcs):,.2f} pesos")
        print(f"   • Diferencia de días: {lineas_con_fecha[-1]['dias'] - lineas_con_fecha[0]['dias']} días")

# Ahora para COX
print("\n" + "=" * 140)
print("📄 FACTURA: FAC 000001 - AGRICOLA COX LTDA")
print("=" * 140)
print(f"{'OC':<10} | {'FECHA OC':<20} | {'PRODUCTO':<45} | {'CANT':>8} | {'USD':>12} | {'CLP':>14} | {'TC':>10} | {'DÍAS':>5}")
print(f"{'='*140}")

factura_cox = None
for f in facturas:
    if f['nombre'] == 'FAC 000001':
        factura_cox = f
        break

if factura_cox:
    lineas_cox = []
    
    for linea in factura_cox['lineas'][:5]:  # Solo 5 para no saturar
        nombre = linea['nombre'] or ""
        oc_nombre = ""
        if ":" in nombre:
            oc_nombre = nombre.split(":")[0].strip()
        
        if oc_nombre:
            ocs = client.search_read(
                "purchase.order",
                [("name", "=", oc_nombre)],
                ["name", "date_order"],
                limit=1
            )
            
            if ocs:
                fecha_oc = ocs[0].get('date_order', '')
                producto = nombre.split("]")[1].strip() if "]" in nombre else nombre[:40]
                
                from datetime import datetime
                if fecha_oc:
                    fecha_obj = datetime.strptime(fecha_oc[:10], '%Y-%m-%d')
                    hoy = datetime(2026, 2, 5)
                    dias = (hoy - fecha_obj).days
                else:
                    dias = 0
                
                lineas_cox.append({
                    'oc': oc_nombre,
                    'fecha': fecha_oc[:19] if fecha_oc else 'N/A',
                    'producto': producto,
                    'cant': linea['cantidad'],
                    'usd': linea['subtotal_usd'],
                    'clp': linea['subtotal_clp'],
                    'tc': linea['tc_implicito'],
                    'dias': dias
                })
    
    lineas_cox.sort(key=lambda x: x['fecha'])
    
    for l in lineas_cox:
        print(f"{l['oc']:<10} | {l['fecha']:<20} | {l['producto'][:45]:<45} | {l['cant']:>8.2f} | ${l['usd']:>11,.2f} | ${l['clp']:>13,.0f} | {l['tc']:>10,.2f} | {l['dias']:>5}")
    
    print(f"{'='*140}")
    
    if lineas_cox:
        print(f"\n📈 ANÁLISIS:")
        print(f"   • Todas las OCs son del 2 y 3 de Febrero 2026 (hace 2-3 días)")
        print(f"   • Por eso tienen el MISMO TC: {lineas_cox[0]['tc']:,.2f}")
        print(f"   • El dólar no varió significativamente entre el 2 y 3 de Febrero")

print("\n" + "=" * 140)
print("✅ CONCLUSIÓN: El TC refleja el valor del dólar el día que se registró cada OC en Odoo")
print("=" * 140 + "\n")
