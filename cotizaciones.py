import yfinance as yf

EMPRESAS_IBEX = {
    "iberdrola": "IBE.MC",
    "santander": "SAN.MC",
    "telefonica": "TEF.MC",
    "repsol": "REP.MC",
    "bbva": "BBVA.MC",
    # Añade más si lo deseas
}

def obtener_ticker(empresa_nombre: str) -> str:
    return EMPRESAS_IBEX.get(empresa_nombre.lower())

def consultar_precio_medio(ticker: str, fecha_inicio: str, fecha_fin: str) -> float:
    df = yf.download(ticker, start=fecha_inicio, end=fecha_fin, progress=False)
    if df.empty:
        return None
    return round(df["Close"].mean(), 2)

def construir_respuesta_yfinance(empresa: str, fecha_inicio: str, fecha_fin: str) -> dict:
    ticker = obtener_ticker(empresa)
    if not ticker:
        return {"respuesta": f"No se encontró el ticker de la empresa '{empresa}'."}

    precio_medio = consultar_precio_medio(ticker, fecha_inicio, fecha_fin)
    if precio_medio is None:
        return {"respuesta": f"No se pudieron obtener datos para {empresa} entre {fecha_inicio} y {fecha_fin}."}

    return {
        "respuesta": f"El precio medio de las acciones de {empresa.capitalize()} entre {fecha_inicio} y {fecha_fin} fue de {precio_medio}€."
    }
