"""
Funciones de formateo chileno para reportes.
"""
from datetime import datetime, date


def fmt_fecha(fecha_str):
    """Convierte fecha ISO a formato DD/MM/AAAA"""
    if not fecha_str:
        return ""
    try:
        if isinstance(fecha_str, (date, datetime)):
            return fecha_str.strftime("%d/%m/%Y")
        if isinstance(fecha_str, str):
            if " " in fecha_str:
                fecha_str = fecha_str.split(" ")[0]
            elif "T" in fecha_str:
                fecha_str = fecha_str.split("T")[0]
            dt = datetime.strptime(fecha_str, "%Y-%m-%d")
            return dt.strftime("%d/%m/%Y")
    except:
        pass
    return str(fecha_str)


def fmt_numero(valor, decimales=0):
    """Formatea número con punto como miles y coma como decimal"""
    if valor is None:
        return "0"
    try:
        if decimales > 0:
            formatted = f"{valor:,.{decimales}f}"
        else:
            formatted = f"{valor:,.0f}"
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return formatted
    except:
        return str(valor)


def fmt_dinero(valor, decimales=0):
    """Formatea valor monetario con símbolo $"""
    return f"${fmt_numero(valor, decimales)}"
