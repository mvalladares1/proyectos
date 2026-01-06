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


# Cache para evitar recargar el Excel en cada petición
from functools import lru_cache
import time

_cache_timestamp = 0
_cache_ttl = 300  # 5 minutos en segundos
_cached_df = None

def _get_cached_proyecciones():
    """Obtiene proyecciones con cache de 5 minutos."""
    global _cache_timestamp, _cached_df
    current_time = time.time()
    
    if _cached_df is None or (current_time - _cache_timestamp) > _cache_ttl:
        _cached_df = _load_proyecciones_from_excel()
        _cache_timestamp = current_time
        print(f"[DEBUG abastecimiento] Cache renovado a las {datetime.now()}")
    
    return _cached_df


def _load_proyecciones_from_excel() -> pd.DataFrame:
    """
    Carga los datos de proyección consolidados del Excel (función interna).
    
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
        'especie': 'especie',
        'precio': 'precio'  # Añadir columna de precio
    })
    
    # Asegurar que existe columna precio (si no, crear con valor 0)
    if 'precio' not in df.columns:
        df['precio'] = 0
    
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
    id_vars = ['productor', 'planta', 'especie', 'precio']  # Incluir precio en id_vars
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
    
    # Normalizar especie: extraer especie_base y manejo
    def normalizar_especie(especie_raw):
        """Extrae especie base y manejo del nombre de especie."""
        if not especie_raw or pd.isna(especie_raw):
            return 'Otro', 'Convencional'
        
        esp = str(especie_raw).upper().strip()
        
        # Detectar manejo
        if 'ORGAN' in esp:
            manejo = 'Orgánico'
        else:
            manejo = 'Convencional'
        
        # Detectar especie base
        if 'ARANDANO' in esp or 'ARÁNDANO' in esp:
            especie_base = 'Arándano'
        elif 'FRAM' in esp or 'FRAMBUESA' in esp or 'MEEKER' in esp or 'HERITAGE' in esp or 'WAKEFIELD' in esp:
            especie_base = 'Frambuesa'
        elif 'FRUTILLA' in esp:
            especie_base = 'Frutilla'
        elif 'MORA' in esp:
            especie_base = 'Mora'
        elif 'CEREZA' in esp:
            especie_base = 'Cereza'
        else:
            especie_base = 'Otro'
        
        return especie_base, manejo
    
    # Aplicar normalización
    df_long[['especie_base', 'manejo']] = df_long['especie'].apply(
        lambda x: pd.Series(normalizar_especie(x))
    )
    
    # Crear campo combinado especie_manejo
    df_long['especie_manejo'] = df_long['especie_base'] + ' ' + df_long['manejo']
    
    return df_long


def load_proyecciones_consolidado() -> pd.DataFrame:
    """
    Carga los datos de proyección consolidados del Excel (con cache).
    El cache se renueva cada 5 minutos.
    """
    return _get_cached_proyecciones().copy()

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
        Lista de diccionarios con datos por semana incluyendo gasto proyectado
    """
    # VALIDACIÓN DE TIPOS: Normalizar planta y especie
    if planta is not None:
        if isinstance(planta, str):
            planta = [planta]
        elif not isinstance(planta, list):
            planta = list(planta) if planta else []
    
    if especie is not None:
        if isinstance(especie, str):
            especie = [especie]
        elif not isinstance(especie, list):
            especie = list(especie) if especie else []
    
    df = load_proyecciones_consolidado()
    
    # Aplicar filtros
    if planta:
        planta_upper = [p.upper() for p in planta]
        df = df[df['planta'].isin(planta_upper)]
    
    if especie:
        # Filtrar por especie_manejo (formato normalizado)
        df = df[df['especie_manejo'].isin(especie)]
    
    # Calcular gasto proyectado por fila (kg × precio)
    df['precio'] = pd.to_numeric(df['precio'], errors='coerce').fillna(0)
    df['gasto_proyectado'] = df['kg_proyectados'] * df['precio']
    
    # Agrupar por semana
    grouped = df.groupby(['semana', 'fecha_semana']).agg({
        'kg_proyectados': 'sum',
        'gasto_proyectado': 'sum'
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
            'kg_proyectados': float(row['kg_proyectados']),
            'gasto_proyectado': float(row['gasto_proyectado'])
        })
    
    return result


def get_proyecciones_por_especie(
    planta: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Obtiene las proyecciones agregadas por especie.
    """
    # VALIDACIÓN DE TIPOS: Normalizar planta
    if planta is not None:
        if isinstance(planta, str):
            planta = [planta]
        elif not isinstance(planta, list):
            planta = list(planta) if planta else []
    
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
    """Retorna lista de especies normalizadas (especie + manejo) disponibles en el Excel."""
    df = load_proyecciones_consolidado()
    return sorted(df['especie_manejo'].dropna().unique().tolist())


def get_semanas_disponibles() -> List[int]:
    """Retorna lista de semanas disponibles en el Excel."""
    df = load_proyecciones_consolidado()
    semanas = df['semana'].unique().tolist()
    # Ordenar: 47-52 primero, luego 1-17
    semanas_ordenadas = sorted([s for s in semanas if s >= 47]) + sorted([s for s in semanas if s < 47])
    return semanas_ordenadas


def get_precios_por_especie(
    planta: Optional[List[str]] = None,
    especie: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Obtiene precios proyectados por especie y manejo (precio único por combinación).
    El precio está asociado a cada fila del Excel y representa el precio por kg.
    
    Returns:
        Lista de diccionarios con especie_manejo y precio_promedio
    """
    # VALIDACIÓN DE TIPOS: Normalizar planta y especie
    if planta is not None:
        if isinstance(planta, str):
            planta = [planta]
        elif not isinstance(planta, list):
            planta = list(planta) if planta else []
    
    if especie is not None:
        if isinstance(especie, str):
            especie = [especie]
        elif not isinstance(especie, list):
            especie = list(especie) if especie else []
    
    df = load_proyecciones_consolidado()
    
    # Aplicar filtros
    if planta:
        planta_upper = [p.upper() for p in planta]
        df = df[df['planta'].isin(planta_upper)]
    
    if especie:
        df = df[df['especie_manejo'].isin(especie)]
    
    # Convertir precio a float, reemplazar 0 por NaN para promediar mejor
    df['precio'] = pd.to_numeric(df['precio'], errors='coerce')
    
    # Agrupar por especie_manejo (incluye tipo fruta + manejo) y obtener precio promedio (ponderado por kg)
    # Precio = suma(precio * kg) / suma(kg)
    df['precio_x_kg'] = df['precio'] * df['kg_proyectados']
    
    # Agrupar por especie_manejo para tener precios específicos por manejo
    grouped = df.groupby('especie_manejo').agg({
        'kg_proyectados': 'sum',
        'precio_x_kg': 'sum'
    }).reset_index()
    
    grouped['precio_promedio'] = grouped.apply(
        lambda row: row['precio_x_kg'] / row['kg_proyectados'] if row['kg_proyectados'] > 0 else 0,
        axis=1
    )
    
    result = []
    for _, row in grouped.iterrows():
        if row['precio_promedio'] > 0:  # Solo incluir si hay precio
            result.append({
                'especie': row['especie_manejo'],  # Ahora incluye manejo
                'precio_proyectado': round(float(row['precio_promedio']), 0),
                'kg_total': float(row['kg_proyectados'])
            })
    
    # Ordenar por kg total descendente
    result.sort(key=lambda x: x['kg_total'], reverse=True)
    return result


def get_precios_detalle_productor(
    planta: Optional[List[str]] = None,
    especie: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Obtiene precios proyectados detallados por PRODUCTOR y especie.
    
    Returns:
        Lista de diccionarios con: productor, especie, precio_proyectado, kg_total
    """
    # VALIDACIÓN DE TIPOS: Normalizar planta y especie
    if planta is not None:
        if isinstance(planta, str):
            planta = [planta]
        elif not isinstance(planta, list):
            planta = list(planta) if planta else []
    
    if especie is not None:
        if isinstance(especie, str):
            especie = [especie]
        elif not isinstance(especie, list):
            especie = list(especie) if especie else []
    
    df = load_proyecciones_consolidado()
    
    # Aplicar filtros
    if planta:
        planta_upper = [p.upper() for p in planta]
        df = df[df['planta'].isin(planta_upper)]
    
    if especie:
        df = df[df['especie_manejo'].isin(especie)]
    
    # Convertir precio a float
    df['precio'] = pd.to_numeric(df['precio'], errors='coerce')
    
    # Calcular monto total para promediar ponderado
    df['precio_x_kg'] = df['precio'] * df['kg_proyectados']
    
    # Agrupar por Productor y Especie
    grouped = df.groupby(['productor', 'especie_manejo']).agg({
        'kg_proyectados': 'sum',
        'precio_x_kg': 'sum'
    }).reset_index()
    
    grouped['precio_promedio'] = grouped.apply(
        lambda row: row['precio_x_kg'] / row['kg_proyectados'] if row['kg_proyectados'] > 0 else 0,
        axis=1
    )
    
    result = []
    for _, row in grouped.iterrows():
        if row['precio_promedio'] > 0:
            result.append({
                'productor': row['productor'],
                'especie': row['especie_manejo'],
                'precio_proyectado': round(float(row['precio_promedio']), 0),
                'kg_total': float(row['kg_proyectados'])
            })
    
    return result
