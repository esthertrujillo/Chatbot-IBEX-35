import yfinance as yf
from datetime import datetime, timedelta
from typing import Tuple, Optional

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

def es_fecha_valida(fecha: str) -> bool:
    try:
        datetime.strptime(fecha, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def ajustar_intervalo_si_fecha_unica(fecha_inicio: str, fecha_fin: str) -> Tuple[str, str, Optional[str]]:
    if fecha_inicio == fecha_fin:
        fecha_obj_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d")
        fecha_anterior = (fecha_obj_dt - timedelta(days=1)).strftime("%Y-%m-%d")
        fecha_posterior = (fecha_obj_dt + timedelta(days=1)).strftime("%Y-%m-%d")
        return fecha_anterior, fecha_posterior, fecha_inicio
    else:
        return fecha_inicio, fecha_fin, None

def consultar_precio_medio(ticker: str, fecha_inicio: str, fecha_fin: str, fecha_objetivo: Optional[str] = None) -> Optional[float]:
    try:
        end_date_inclusive = (datetime.strptime(fecha_fin, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        df = yf.download(ticker, start=fecha_inicio, end=end_date_inclusive, progress=False, auto_adjust=True)

        print(f"\n📊 Resultado bruto de YFinance para {ticker} ({fecha_inicio} a {end_date_inclusive}):")
        print(df)

        if df.empty:
            print(f"⚠️ No se encontraron datos para {ticker} en el rango especificado.")
            return None

        if fecha_objetivo:
            df_fecha = df[df.index.strftime("%Y-%m-%d") == fecha_objetivo]
            print(f"\n📌 Datos filtrados para {fecha_objetivo}:")
            print(df_fecha)

            if df_fecha.empty:
                print(f"⚠️ No se encontraron datos para {ticker} en la fecha objetivo {fecha_objetivo} (puede ser fin de semana/festivo).")
                return None

            precio_medio = float(df_fecha["Close"].iloc[0])
        else:
            precio_medio = float(df["Close"].mean())

        return round(precio_medio, 2)

    except Exception as e:
        print(f"⚠️ Error al consultar datos para {ticker}: {e}")
        return None

def construir_respuesta_yfinance(empresa: str, fecha_inicio: str, fecha_fin: str) -> dict:
    ticker = obtener_ticker(empresa)
    if not ticker:
        return {"respuesta": f"❌ No se encontró el ticker de la empresa '{empresa}'."}

    if not (es_fecha_valida(fecha_inicio) and es_fecha_valida(fecha_fin)):
        return {"respuesta": "❌ Formato de fecha inválido. Asegúrate de usar YYYY-MM-DD."}

    if datetime.strptime(fecha_inicio, "%Y-%m-%d") > datetime.strptime(fecha_fin, "%Y-%m-%d"):
        return {"respuesta": "❌ La fecha de inicio no puede ser posterior a la fecha de fin."}

    fecha_inicio_adj, fecha_fin_adj, fecha_objetivo = ajustar_intervalo_si_fecha_unica(fecha_inicio, fecha_fin)

    precio_medio = consultar_precio_medio(ticker, fecha_inicio_adj, fecha_fin_adj, fecha_objetivo)

    if precio_medio is None:
        if fecha_objetivo:
            return {"respuesta": f"⚠️ No se encontraron datos para **{empresa.capitalize()}** en la fecha **{fecha_objetivo}**. Podría ser un fin de semana o festivo, o no hay datos disponibles."}
        else:
            return {"respuesta": f"⚠️ No se pudieron obtener datos para **{empresa.capitalize()}** entre **{fecha_inicio}** y **{fecha_fin}**."}

    if fecha_objetivo:
        return {
            "respuesta": f"✅ El precio de cierre de las acciones de **{empresa.capitalize()}** el **{fecha_objetivo}** fue de **{precio_medio} €**."
        }
    else:
        return {
            "respuesta": f"El precio medio de las acciones de **{empresa.capitalize()}** entre **{fecha_inicio}** y **{fecha_fin}** fue de **{precio_medio} €**."
        }
