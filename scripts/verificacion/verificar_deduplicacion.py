"""
Verificar que duplicados fueron correctamente eliminados
"""
import pandas as pd
import glob
import os

archivos = glob.glob('stock_teorico_detalle_*.xlsx')
if not archivos:
    print("❌ No se encontró ningún archivo Excel")
    exit(1)

archivo_reciente = max(archivos, key=os.path.getmtime)
print(f"📂 Archivo: {archivo_reciente}\n")

df_compras = pd.read_excel(archivo_reciente, sheet_name='Compras Detalle')

print(f"📊 Total líneas de compras: {len(df_compras):,}\n")

# Buscar FAC 000030
fac_30 = df_compras[df_compras['Factura'].str.contains('FAC 000030', na=False)]

if len(fac_30) > 0:
    print(f"🔍 FAC 000030 - {len(fac_30)} líneas:")
    print(fac_30[['Factura', 'Producto ID', 'Producto', 'Cuenta', 'Cantidad (kg)', 'Monto']].head(20).to_string(index=False))
    
    # Ver cuentas únicas
    print(f"\n📋 Cuentas en FAC 000030:")
    print(fac_30['Cuenta'].value_counts().to_string())
    
    # Análisis de duplicados
    print(f"\n📊 AGRUPACIÓN POR PRODUCTO:")
    duplicados = fac_30.groupby(['Producto ID']).agg({
        'Cantidad (kg)': ['count', 'sum'],
        'Monto': 'sum',
        'Cuenta': lambda x: list(set(x))
    }).reset_index()
    duplicados.columns = ['Producto ID', 'Líneas', 'Total kg', 'Total Monto', 'Cuentas']
    print(duplicados.to_string(index=False))

# Análisis de cuentas en compras
print(f"\n\n📋 CUENTAS CONTABLES EN TODAS LAS COMPRAS:")
cuentas = df_compras['Cuenta'].value_counts()
print(cuentas.to_string())

# Verificar 2022
print(f"\n\n📅 COMPRAS 2022:")
compras_2022 = df_compras[df_compras['Año'] == 2022]
print(f"Total líneas 2022: {len(compras_2022)}")
print(f"Total kg 2022: {compras_2022['Cantidad (kg)'].sum():,.2f} kg")
print(f"Total $ 2022: ${compras_2022['Monto'].sum():,.0f}")
