import pandas as pd

ventas = pd.read_excel('stock_teorico_detalle_20260127_121251.xlsx', sheet_name='Ventas Detalle')

print(f'\n📊 Total ventas: {len(ventas)} líneas')
print(f'📊 Total kg: {ventas["Cantidad (kg)"].sum():,.2f} kg')
print(f'📊 Total valor: ${ventas["Monto"].sum():,.0f}')

print(f'\n🔍 Verificando FCXE 000002:')
fcxe002 = ventas[ventas['Factura'].str.contains('FCXE 000002', na=False)]
print(f'   Líneas: {len(fcxe002)}')
if len(fcxe002) > 0:
    print(f'   Kg: {fcxe002["Cantidad (kg)"].sum():,.2f}')
    print(f'   Valor: ${fcxe002["Monto"].sum():,.0f}')
    print('\n   Detalle:')
    for _, row in fcxe002.iterrows():
        print(f'     {row["Producto"][:50]:50s} | {row["Cantidad (kg)"]:8.2f} kg | ${row["Monto"]:12,.0f}')
else:
    print('   ❌ NO ENCONTRADA')

print(f'\n🔍 Verificando FCXE 000007:')
fcxe007 = ventas[ventas['Factura'].str.contains('FCXE 000007', na=False)]
print(f'   Líneas: {len(fcxe007)}')
if len(fcxe007) > 0:
    print(f'   Kg: {fcxe007["Cantidad (kg)"].sum():,.2f}')
    print(f'   Valor: ${fcxe007["Monto"].sum():,.0f}')
    print('\n   Detalle:')
    for _, row in fcxe007.iterrows():
        print(f'     {row["Producto"][:50]:50s} | {row["Cantidad (kg)"]:8.2f} kg | ${row["Monto"]:12,.0f}')
else:
    print('   ❌ NO ENCONTRADA')

print(f'\n🔍 Cuenta 43010111:')
cuenta_otros = ventas[ventas['Cuenta'].str.contains('43010111', na=False)]
print(f'   Líneas: {len(cuenta_otros)}')
if len(cuenta_otros) > 0:
    print(f'   Valor total: ${cuenta_otros["Monto"].sum():,.0f}')
    print('\n   Detalle:')
    for _, row in cuenta_otros.head(10).iterrows():
        print(f'     {row["Factura"]:15s} | {str(row["Fecha"]):10s} | ${row["Monto"]:12,.0f} | {row["Producto"]}')
