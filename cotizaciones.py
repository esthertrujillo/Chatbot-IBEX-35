import yfinance as yf
from datetime import datetime

EMPRESAS_IBEX = {
    "acciona": "ANA.MC",
    "acciona energía": "ANE.MC",
    "acerinox": "ACX.MC",
    "acs": "ACS.MC",
    "aena": "AENA.MC",
    "amadeus": "AMS.MC",
    "arcelormittal": "MTS.MC",
    "bankinter": "BKT.MC",
    "bbva": "BBVA.MC",
    "caixabank": "CABK.MC",
    "cellnex telecom": "CLNX.MC",
    "enagas": "ENG.MC",
    "endesa": "ELE.MC",
    "ferrovial": "FER.MC",
    "fluidra": "FDR.MC",
    "grifols": "GRF.MC",
    "iag": "IAG.MC",
    "iberdrola": "IBE.MC",
    "inditex": "ITX.MC",
    "indra": "IDR.MC",
    "inm. colonial": "COL.MC",
    "laboratorios farma (rovi)": "ROVI.MC",
    "logista": "LOG.MC",
    "mapfre": "MAP.MC",
    "merlin properties": "MRL.MC",
    "naturgy": "NTGY.MC",
    "puig": "PUIG.MC",  # Ticker reciente tras su salida a bolsa
    "ree": "RED.MC",    # Red Eléctrica Española, ahora Redeia
    "repsol": "REP.MC",
    "sabadell": "SAB.MC",
    "sacyr": "SCYR.MC",
    "santander": "SAN.MC",
    "solaria energia": "SLR.MC",
    "telefonica": "TEF.MC",
    "unicaja banco": "UNI.MC"
}

def obtener_ticker(empresa_nombre: str) -> str:
    return EMPRESAS_IBEX.get(empresa_nombre.lower())

# Recibe el nombre y maneja mayúsculas/minúsculas para evitar errores del usuario

def es_fecha_valida(fecha: str) -> bool:
    try:
        datetime.strptime(fecha, "%Y-%m-%d")
        return True
    except:
        return False
# Comprueba si una fecha está en formato correcto

def consultar_precio_medio(ticker: str, fecha_inicio: str, fecha_fin: str) -> float:
    df = yf.download(ticker, start=fecha_inicio, end=fecha_fin, progress=False)

    if df.empty:
        return None

    try:
        precio_medio = df["Close"].mean()
        return round(float(precio_medio), 2)
    except Exception:
        return None
#Descarga los datos históricos desde Yahoo Finance entre las fechas indicadas 
#y calcula el precio medio de cierre (Close) en ese periodo. 


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

#finalmente llamada a la api y da la respuesta 