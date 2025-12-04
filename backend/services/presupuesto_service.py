"""Servicio de Presupuesto y comparación con el Estado de Resultado"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
import traceback

import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

PPTO_2025_PATH = DATA_DIR / "BD_PPTO_2025.xlsx"
PPTO_2026_PATH = DATA_DIR / "BD_PPTO_2026.xlsx"


def _leer_excel(path: Path, sheet: Optional[str] = None) -> pd.DataFrame:
    kwargs = {"sheet_name": sheet} if sheet else {}
    return pd.read_excel(path, **kwargs)


def cargar_presupuesto_2025(filepath: Optional[Path] = None) -> pd.DataFrame | Dict[str, str]:
    path = filepath or PPTO_2025_PATH
    try:
        try:
            df = pd.read_excel(path, sheet_name="PPTO En uso", header=0)
        except ValueError:
            df = pd.read_excel(path, sheet_name=0, header=0)

        columnas_rename = {
            "Nuero de fila": "numero_fila",
            "Area": "area",
            "Sala": "sala",
            "Cargo": "cargo",
            "Centro de costo": "centro_costo",
            "Detalle": "detalle",
            "Ppto": "ppto_tipo",
            "N° Cuenta": "cuenta_codigo",
            "Cuenta": "cuenta_nombre",
            "Un. Med": "unidad_medida",
            "Moneda": "moneda",
            "Nombre Completo": "nombre_completo",
            "Cat 1 IFRS": "cat_ifrs_1",
            "Cat IFRS 2 vf": "cat_ifrs_2",
            "Cat IFRS 3": "cat_ifrs_3",
            "Cat IFRS 4": "cat_ifrs_4",
            "Fecha EERR": "fecha_eerr",
            "Fecha Fujo": "fecha_flujo",
            "Cantidad": "cantidad",
            "Monto con Signo": "monto"
        }
        df = df.rename(columns=columnas_rename)
        return df
    except FileNotFoundError:
        return {"error": f"Archivo no encontrado: {path}"}
    except Exception as exc:
        return {"error": str(exc)}


def cargar_presupuesto_2026(filepath: Optional[Path] = None) -> pd.DataFrame | Dict[str, str]:
    path = filepath or PPTO_2026_PATH
    try:
        df = pd.read_excel(path, sheet_name="BD", header=0)
        columnas_rename = {
            "EMPRESA": "empresa",
            "CENTRO DE COSTO": "centro_costo",
            "ÁREA": "area",
            "PPTO": "ppto_tipo",
            "CARGO": "cargo",
            "DETALLE": "detalle",
            "SKU": "sku",
            "N° CUENTA": "cuenta_codigo",
            "NOMBRE CUENTA CONTABLE": "cuenta_nombre",
            "UND": "unidad_medida",
            "MONEDA": "moneda",
            "PRECIO": "precio",
            "Fecha EERR": "fecha_eerr",
            "UNIDADES": "unidades",
            "MONTO": "monto"
        }
        df = df.rename(columns=columnas_rename)
        return df
    except FileNotFoundError:
        return {"error": f"Archivo no encontrado: {path}"}
    except Exception as exc:
        return {"error": str(exc)}


def procesar_presupuesto_mensual(df_ppto: pd.DataFrame, año: int = 2025) -> Dict[str, Dict[str, float]] | Dict[str, str]:
    df = df_ppto.copy()
    if "fecha_eerr" not in df.columns:
        return {"error": "Columna fecha_eerr no encontrada"}

    try:
        df["fecha_eerr"] = pd.to_datetime(df["fecha_eerr"], format="%d/%m/%Y", errors="coerce")
        if df["fecha_eerr"].isna().all():
            df["fecha_eerr"] = pd.to_datetime(df["fecha_eerr"], errors="coerce")
        df = df[df["fecha_eerr"].dt.year == año]
        df["mes"] = df["fecha_eerr"].dt.strftime("%Y-%m")

        categorias_principales = [
            "1 - INGRESOS", "2 - COSTOS", "4 - GASTOS DIRECTOS",
            "6 - GAV", "8 - INTERESES", "10 - INGRESOS NO OPERACIONALES",
            "11 - GASTOS NO OPERACIONALES"
        ]

        def clasificar_categoria(cat_ifrs_1: Optional[str]) -> Optional[str]:
            if not cat_ifrs_1:
                return None
            valor = str(cat_ifrs_1).upper().strip()
            for cat in categorias_principales:
                if cat in valor or valor.startswith(cat.split(" ")[0]):
                    return cat
            if valor.startswith("1"):
                return "1 - INGRESOS"
            if valor.startswith("2"):
                return "2 - COSTOS"
            if valor.startswith("4"):
                return "4 - GASTOS DIRECTOS"
            if valor.startswith("6"):
                return "6 - GAV"
            if valor.startswith("8"):
                return "8 - INTERESES"
            if valor.startswith("10"):
                return "10 - INGRESOS NO OPERACIONALES"
            if valor.startswith("11"):
                return "11 - GASTOS NO OPERACIONALES"
            return None

        col_cat1 = "cat_ifrs_1" if "cat_ifrs_1" in df.columns else "Cat 1 IFRS"

        def monto_ok(row: pd.Series) -> float:
            monto = row.get("monto", 0) or 0
            cat1 = str(row.get(col_cat1, "")).upper()
            if "1 - INGRESOS" in cat1 or cat1.startswith("1"):
                return monto
            return monto * -1

        df["categoria_principal"] = df[col_cat1].apply(clasificar_categoria)
        df["monto_ok"] = df.apply(monto_ok, axis=1)

        datos_mensuales: Dict[str, Dict[str, float]] = {}
        for mes, grupo in df.groupby("mes"):
            datos_mensuales[mes] = {cat: 0.0 for cat in categorias_principales}
            for cat in categorias_principales:
                datos_mensuales[mes][cat] = float(grupo[grupo["categoria_principal"] == cat]["monto_ok"].sum())

        ytd = {cat: 0.0 for cat in categorias_principales}
        for mes_data in datos_mensuales.values():
            for cat, valor in mes_data.items():
                ytd[cat] += valor

        return {"mensual": datos_mensuales, "ytd": ytd}
    except Exception as exc:
        return {"error": f"{exc}\n{traceback.format_exc()}"}


def get_presupuesto(año: int = 2025, mes: Optional[str] = None, centro_costo: Optional[str] = None) -> Dict[str, Any]:
    if año == 2025:
        df = cargar_presupuesto_2025()
    elif año == 2026:
        df = cargar_presupuesto_2026()
    else:
        return {"error": f"Año {año} no disponible"}

    if isinstance(df, dict) and "error" in df:
        return df

    if centro_costo and "centro_costo" in df.columns:
        df = df[df["centro_costo"] == centro_costo]

    if mes and "fecha_eerr" in df.columns:
        df = df.copy()
        df["fecha_eerr"] = pd.to_datetime(df["fecha_eerr"], errors="coerce")
        df = df[df["fecha_eerr"].dt.strftime("%Y-%m") == mes]

    resultado = procesar_presupuesto_mensual(df, año)
    if isinstance(resultado, dict) and "error" in resultado:
        return resultado

    resultado["total_registros"] = len(df)
    return resultado


def comparar_real_vs_ppto(datos_reales: Dict[str, float], datos_ppto: Dict[str, float]) -> Dict[str, Dict[str, float]]:
    categorias = [
        "1 - INGRESOS", "2 - COSTOS", "4 - GASTOS DIRECTOS",
        "6 - GAV", "8 - INTERESES", "10 - INGRESOS NO OPERACIONALES",
        "11 - GASTOS NO OPERACIONALES"
    ]

    comparacion: Dict[str, Dict[str, float]] = {}
    for cat in categorias:
        real = datos_reales.get(cat, 0.0)
        ppto = datos_ppto.get(cat, 0.0)
        diferencia = real - ppto
        porcentaje = (diferencia / ppto * 100) if ppto != 0 else 0.0
        comparacion[cat] = {
            "real": real,
            "ppto": ppto,
            "diferencia": diferencia,
            "porcentaje": porcentaje
        }
    return comparacion
