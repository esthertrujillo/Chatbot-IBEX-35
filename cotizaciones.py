import yfinance as yf
from datetime import datetime

EMPRESAS_IBEX = {
    "iberdrola": "IBE.MC",
    "santander": "SAN.MC",
    "telefonica": "TEF.MC",
    "repsol": "REP.MC",
    "bbva": "BBVA.MC",
    # Puedes añadir más empresas si lo deseas
}

def obtener_ticker(empresa_nombre: str) -> str:
    return EMPRESAS_IBEX.get(empresa_nombre.lower())

def es_fecha_valida(fecha: str) -> bool:
    try:
        datetime.strptime(fecha, "%Y-%m-%d")
        return True
    except:
        return False

def consultar_precio_medio(ticker: str, fecha_inicio: str, fecha_fin: str) -> float:
    df = yf.download(ticker, start=fecha_inicio, end=fecha_fin, progress=False)

    if df.empty:
        return None

    try:
        precio_medio = df["Close"].mean()
        return round(float(precio_medio), 2)
    except Exception:
        return None

def construir_respuesta_yfinance(empresa: str, fecha_inicio: str, fecha_fin: str) -> dict:
    ticker = obtener_ticker(empresa)
    if not ticker:
        return {"respuesta": f"❌ No se encontró el ticker de la empresa '{empresa}'."}

    if not (es_fecha_valida(fecha_inicio) and es_fecha_valida(fecha_fin)):
        return {"respuesta": "❌ Formato de fecha inválido. Usa YYYY-MM-DD."}

    precio_medio = consultar_precio_medio(ticker, fecha_inicio, fecha_fin)
    if precio_medio is None:
        return {"respuesta": f"⚠️ No se pudieron obtener datos para {empresa} entre {fecha_inicio} y {fecha_fin}."}

    return {
        "respuesta": f"✅ El precio medio de las acciones de {empresa.capitalize()} entre {fecha_inicio} y {fecha_fin} fue de {precio_medio}€."
    }
