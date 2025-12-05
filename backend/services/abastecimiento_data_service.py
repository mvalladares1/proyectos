import pandas as pd
import requests
from io import BytesIO

def load_budget_data(file_or_path):
    try:
        df = pd.read_excel(file_or_path, sheet_name="Hoja1")
        if "KILOS" in df.columns:
            df = df.rename(columns={"KILOS": "PPTO"})
        if "Code" in df.columns:
            df = df.drop(columns=["Code"])
        required_columns = ["PPTO", "ESTADO", "PRODUCTO", "VARIEDAD", "MANEJO"]
        missing_cols = [col for col in required_columns if col not in df.columns]
        if "FECHAS MOD" not in df.columns and "MES" not in df.columns:
            missing_cols.append("FECHAS MOD or MES")
        if missing_cols:
            raise ValueError(f"El archivo no tiene la estructura correcta. Faltan las columnas: {', '.join(missing_cols)}")
        return df
    except FileNotFoundError:
        print(f"File not found: {file_or_path}")
        return pd.DataFrame()
    except ValueError as ve:
        raise ve
    except Exception as e:
        print(f"Error loading budget data: {e}")
        raise ValueError(f"Error al leer el archivo Excel: {e}")

def load_dates_data(file_or_path):
    try:
        df = pd.read_excel(file_or_path, sheet_name="Fechas")
        df = df.dropna(how='all')
        required_columns = ["Fecha", "Semana"]
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            raise ValueError(f"El archivo de Fechas no tiene la estructura correcta. Faltan las columnas: {', '.join(missing_cols)}")
        if "Fecha" in df.columns:
            df["Fecha"] = pd.to_datetime(df["Fecha"])
        if "Semana" in df.columns:
            df["Semana"] = pd.to_numeric(df["Semana"], errors='coerce')
        return df
    except FileNotFoundError:
        print(f"File not found: {file_or_path}")
        return pd.DataFrame()
    except ValueError as ve:
        raise ve
    except Exception as e:
        print(f"Error loading dates data: {e}")
        raise ValueError(f"Error al leer el archivo de Fechas: {e}")

def load_budget_2026_data(file_or_path):
    try:
        df = pd.read_excel(file_or_path, sheet_name="Hoja1")
        if "Mes" not in df.columns:
             raise ValueError("El archivo de Presupuesto Futuro debe tener la columna 'Mes'.")
        if "Mes" in df.columns:
            df["Mes"] = pd.to_datetime(df["Mes"])
        return df
    except FileNotFoundError:
        print(f"File not found: {file_or_path}")
        return pd.DataFrame()
    except ValueError as ve:
        raise ve
    except Exception as e:
        print(f"Error loading budget 2026 data: {e}")
        raise ValueError(f"Error al leer el archivo de Presupuesto Futuro: {e}")

def get_central_bank_data():
    url = "https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx"
    params = {
        "user": "fhorst@riofuturo.cl",
        "pass": "PowerBi2025",
        "firstdate": "2024-08-01",
        "lastdate": "2025-12-31",
        "timeseries": "F073.TCO.PRE.Z.D",
        "function": "GetSeries"
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if 'Series' in data and 'Obs' in data['Series']:
            obs = data['Series']['Obs']
            df = pd.DataFrame(obs)
            df['value'] = df['value'].astype(str).str.replace(',', '.').astype(float)
            df['indexDateString'] = pd.to_datetime(df['indexDateString'], format='%d-%m-%Y')
            return df
        return pd.DataFrame()
    except Exception as e:
        print(f"Error fetching Central Bank data: {e}")
        return pd.DataFrame()
