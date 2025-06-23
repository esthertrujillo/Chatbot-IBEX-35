import yfinance as yf
from datetime import datetime, timedelta
from typing import Tuple, Optional # <--- Add Optional here

EMPRESAS_IBEX = {
    "iberdrola": "IBE.MC",
    "santander": "SAN.MC",
    "telefonica": "TEF.MC",
    "repsol": "REP.MC",
    "bbva": "BBVA.MC",
    # Add more IBEX 35 companies as needed
}

def obtener_ticker(empresa_nombre: str) -> str:
    """
    Obtiene el ticker de Yahoo Finance para una empresa del IBEX 35.
    """
    return EMPRESAS_IBEX.get(empresa_nombre.lower())

def es_fecha_valida(fecha: str) -> bool:
    """
    Verifica si una cadena de texto es una fecha válida en formato YYYY-MM-DD.
    """
    try:
        datetime.strptime(fecha, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def ajustar_intervalo_si_fecha_unica(fecha_inicio: str, fecha_fin: str) -> Tuple[str, str, str]:
    """
    Si fecha_inicio == fecha_fin, amplía el rango (día anterior, día posterior)
    y devuelve (nuevo_inicio, nuevo_fin, fecha_objetivo).
    fecha_objetivo será la fecha original si el rango se amplió, None en caso contrario.
    """
    if fecha_inicio == fecha_fin:
        fecha_obj_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d")
        fecha_anterior_dt = fecha_obj_dt - timedelta(days=1)
        fecha_posterior_dt = fecha_obj_dt + timedelta(days=1)

        fecha_anterior = fecha_anterior_dt.strftime("%Y-%m-%d")
        fecha_posterior = fecha_posterior_dt.strftime("%Y-%m-%d")
        return fecha_anterior, fecha_posterior, fecha_inicio
    else:
        return fecha_inicio, fecha_fin, None

def consultar_precio_medio(ticker: str, fecha_inicio: str, fecha_fin: str, fecha_objetivo: str = None) -> Optional[float]:
    """
    Consulta el precio de cierre medio para un ticker en un rango de fechas.
    Si se proporciona fecha_objetivo, intenta obtener el precio para ese día específico dentro del rango.
    """
    try:
        # yfinance `end` parameter is exclusive, so add a day to include the `fecha_fin` date
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
            precio_medio = df_fecha["Close"].iloc[0]
        else:
            precio_medio = df["Close"].mean()

        return round(precio_medio, 2)
    except Exception as e:
        print(f"⚠️ Error al consultar datos para {ticker}: {e}")
        return None

def construir_respuesta_yfinance(empresa: str, fecha_inicio: str, fecha_fin: str) -> dict:
    """
    Construye la respuesta para el chatbot usando datos de Yahoo Finance.
    """
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
            return {"respuesta": f"⚠️ No se encontraron datos para {empresa.capitalize()} en la fecha '{fecha_objetivo}'. Podría ser un fin de semana o festivo, o no hay datos disponibles."}
        else:
            return {"respuesta": f"⚠️ No se pudieron obtener datos para {empresa.capitalize()} entre {fecha_inicio} y {fecha_fin}."}

    if fecha_objetivo:
        return {
            "respuesta": f"✅ El precio de cierre de las acciones de {empresa.capitalize()} el {fecha_objetivo} fue de {precio_medio} €."
        }
    else:
        return {
            "respuesta": f"✅ El precio medio de las acciones de {empresa.capitalize()} entre {fecha_inicio} y {fecha_fin} fue de {precio_medio} €."
        }