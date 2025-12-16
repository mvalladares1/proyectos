"""
Servicio para cargar y procesar datos de abastecimiento proyectado
desde el Excel de planificación de recepciones.
"""
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import os

# Ruta del archivo Excel de abastecimiento - buscar en múltiples ubicaciones
def _get_excel_path():
    """Busca el Excel en múltiples ubicaciones posibles."""
    possible_paths = [
        # Ruta relativa desde el servicio
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'recepcion abastecimiento tentativa V3.xlsx'),
        # Ruta desde variable de entorno si existe
        os.path.join(os.getenv('APP_ROOT', '/home/debian/rio-futuro-dashboards/app'), 'data', 'recepcion abastecimiento tentativa V3.xlsx'),
        # Ruta absoluta común en Linux
        '/home/debian/rio-futuro-dashboards/app/data/recepcion abastecimiento tentativa V3.xlsx',
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"[DEBUG abastecimiento] Excel encontrado en: {path}")
            return path
    
    # Si no se encuentra, retornar la primera opción y dejar que falle con mensaje claro
    print(f"[DEBUG abastecimiento] Excel NO encontrado. Rutas probadas: {possible_paths}")
    return possible_paths[0]

ABASTECIMIENTO_EXCEL_PATH = _get_excel_path()

# Mapeo de semanas a fechas de inicio (temporada 2024-2025)
# Semana 47 de 2024 = 18 de noviembre 2024, etc.
def _get_week_start_date(week_num: int) -> datetime:
    """
    Convierte número de semana a fecha de inicio.
    Semanas 47-52 son del año 2024, semanas 1-17 son de 2025.
    """
    if week_num >= 47:
        # Semanas de 2024
        year = 2024
        # Semana 47 comienza el 18 de noviembre 2024
        base_date = datetime(2024, 11, 18)
        weeks_offset = week_num - 47
    else:
        # Semanas de 2025
        year = 2025
        # Semana 1 de 2025 comienza el 30 de diciembre 2024 (o 6 enero según ISO)
        base_date = datetime(2024, 12, 30)
        weeks_offset = week_num - 1
    
    return base_date + timedelta(weeks=weeks_offset)


def load_proyecciones_consolidado() -> pd.DataFrame:
    """
    Carga los datos de proyección consolidados del Excel.
    
    Returns:
        DataFrame con columnas: productor, planta, especie, semana, kg_proyectados
    """
    if not os.path.exists(ABASTECIMIENTO_EXCEL_PATH):
        raise FileNotFoundError(f"No se encontró el archivo de abastecimiento: {ABASTECIMIENTO_EXCEL_PATH}")
    
    # Leer hoja CONSOLIDADO con header en fila 1 (index 1)
    df = pd.read_excel(ABASTECIMIENTO_EXCEL_PATH, sheet_name='CONSOLIDADO', header=1)
    
    # Identificar columnas de semanas (numéricas: 47, 48, ..., 52, 1, 2, ..., 17)
    week_columns = []
    for col in df.columns:
        if isinstance(col, (int, float)) and not pd.isna(col):
            week_columns.append(int(col))
    
    # Renombrar columnas principales
    df = df.rename(columns={
        'Etiquetas de fila': 'productor',
        'PLANTA': 'planta',
        'especie': 'especie'
    })
    
    # Filtrar filas con datos válidos
    df = df[df['productor'].notna() & (df['productor'] != '')]
    df = df[df['planta'].notna() & (df['planta'] != '')]
    
    # Convertir de formato ancho a largo (melt)
    # Crear lista de columnas de semanas como strings para el melt
    week_cols_str = [str(int(w)) if isinstance(w, float) else str(w) for w in week_columns]
    
    # Renombrar las columnas de semanas a strings para facilitar melt
    rename_dict = {col: str(int(col)) if isinstance(col, float) else str(col) 
                   for col in df.columns if isinstance(col, (int, float)) and not pd.isna(col)}
    df = df.rename(columns=rename_dict)
    
    # Hacer melt para convertir semanas a filas
    id_vars = ['productor', 'planta', 'especie']
    value_vars = [c for c in df.columns if c.isdigit()]
    
    df_long = df.melt(
        id_vars=id_vars,
        value_vars=value_vars,
        var_name='semana',
        value_name='kg_proyectados'
    )
    
    # Convertir semana a int y kg a float
    df_long['semana'] = df_long['semana'].astype(int)
    df_long['kg_proyectados'] = pd.to_numeric(df_long['kg_proyectados'], errors='coerce').fillna(0)
    
    # Filtrar filas sin kg proyectados
    df_long = df_long[df_long['kg_proyectados'] > 0]
    
    # Agregar fecha de inicio de semana
    df_long['fecha_semana'] = df_long['semana'].apply(_get_week_start_date)
    
    # Normalizar planta a mayúsculas
    df_long['planta'] = df_long['planta'].str.upper().str.strip()
    
    return df_long


def get_proyecciones_por_semana(
    planta: Optional[List[str]] = None,
    especie: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Obtiene las proyecciones agregadas por semana.
    
    Args:
        planta: Lista de plantas a filtrar (RFP, VILKUN)
        especie: Lista de especies a filtrar (Arándano, Frambuesa, etc.)
    
    Returns:
        Lista de diccionarios con datos por semana
    """
    df = load_proyecciones_consolidado()
    
    # Aplicar filtros
    if planta:
        planta_upper = [p.upper() for p in planta]
        df = df[df['planta'].isin(planta_upper)]
    
    if especie:
        df = df[df['especie'].isin(especie)]
    
    # Agrupar por semana
    grouped = df.groupby(['semana', 'fecha_semana']).agg({
        'kg_proyectados': 'sum'
    }).reset_index()
    
    # Ordenar por semana (47-52 primero, luego 1-17)
    def sort_key(x):
        return x if x >= 47 else x + 100
    
    grouped['sort_key'] = grouped['semana'].apply(sort_key)
    grouped = grouped.sort_values('sort_key').drop(columns=['sort_key'])
    
    result = []
    for _, row in grouped.iterrows():
        result.append({
            'semana': int(row['semana']),
            'fecha_semana': row['fecha_semana'].strftime('%Y-%m-%d'),
            'kg_proyectados': float(row['kg_proyectados'])
        })
    
    return result


def get_proyecciones_por_especie(
    planta: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Obtiene las proyecciones agregadas por especie.
    """
    df = load_proyecciones_consolidado()
    
    if planta:
        planta_upper = [p.upper() for p in planta]
        df = df[df['planta'].isin(planta_upper)]
    
    grouped = df.groupby(['especie']).agg({
        'kg_proyectados': 'sum'
    }).reset_index()
    
    result = []
    for _, row in grouped.iterrows():
        result.append({
            'especie': row['especie'],
            'kg_proyectados': float(row['kg_proyectados'])
        })
    
    return result


def get_especies_disponibles() -> List[str]:
    """Retorna lista de especies únicas disponibles en el Excel."""
    df = load_proyecciones_consolidado()
    return sorted(df['especie'].dropna().unique().tolist())


def get_semanas_disponibles() -> List[int]:
    """Retorna lista de semanas disponibles en el Excel."""
    df = load_proyecciones_consolidado()
    semanas = df['semana'].unique().tolist()
    # Ordenar: 47-52 primero, luego 1-17
    semanas_ordenadas = sorted([s for s in semanas if s >= 47]) + sorted([s for s in semanas if s < 47])
    return semanas_ordenadas
