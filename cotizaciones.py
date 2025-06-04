import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd

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

def consultar_precio_medio(ticker: str, fecha_inicio: str, fecha_fin: str) -> tuple:
    df = yf.download(ticker, start=fecha_inicio, end=fecha_fin, progress=False, group_by="ticker")

    if df.empty:
        fecha_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d")
        nueva_fecha_inicio = (fecha_dt - timedelta(days=2)).strftime("%Y-%m-%d")
        nueva_fecha_fin = (fecha_dt + timedelta(days=2)).strftime("%Y-%m-%d")
        df = yf.download(ticker, start=nueva_fecha_inicio, end=nueva_fecha_fin, progress=False, group_by="ticker")

        if df.empty:
            print(f"\n📥 RAW DATA FROM YFINANCE para {ticker} ({fecha_inicio} → {fecha_fin}):")
            print(df)
            return None, None

    print(f"\n📥 RAW DATA FROM YFINANCE para {ticker} ({fecha_inicio} → {fecha_fin}):")
    print(df)

    try:
        if isinstance(df.columns, pd.MultiIndex):
            close_series = df[ticker]["Close"]
        else:
            close_series = df["Close"]

        df_filtrado = close_series.loc[fecha_inicio:fecha_fin]
        if df_filtrado.empty:
            return None, None

        print("\n📊 CÁLCULO DEL PRECIO MEDIO (valores de cierre utilizados):")
        for fecha, valor in df_filtrado.items():
            print(f"📅 {fecha.date()} → {valor:.4f}€")

        precio_medio = df_filtrado.mean()
        fecha_real = df_filtrado.index[0].strftime("%Y-%m-%d")

        print(f"\n📈 MEDIA CALCULADA = {precio_medio:.4f}€ (basada en {len(df_filtrado)} día/s)")
        print(f"📆 Fecha utilizada para cálculo: {fecha_real}")

        return round(float(precio_medio), 2), fecha_real
    except Exception as e:
        print(f"❌ Error procesando precios: {e}")
        return None, None


def construir_respuesta_yfinance(empresa: str, fecha_inicio: str, fecha_fin: str) -> dict:
    ticker = obtener_ticker(empresa)
    if not ticker:
        return {"respuesta": f"❌ No se encontró el ticker de la empresa '{empresa}'."}

    if not (es_fecha_valida(fecha_inicio) and es_fecha_valida(fecha_fin)):
        return {"respuesta": "❌ Formato de fecha inválido. Usa YYYY-MM-DD."}

    precio, fecha_real = consultar_precio_medio(ticker, fecha_inicio, fecha_fin)
    if precio is None:
        return {"respuesta": f"⚠️ No se pudieron obtener datos para {empresa} entre {fecha_inicio} y {fecha_fin}."}

    if fecha_inicio == fecha_fin:
        return {
            "respuesta": f"✅ El precio de cierre de las acciones de {empresa.capitalize()} el {fecha_real} fue de {precio}€."
        }
    else:
        return {
            "respuesta": f"✅ El precio medio de las acciones de {empresa.capitalize()} entre {fecha_inicio} y {fecha_fin} fue de {precio}€ (calculado desde datos disponibles a partir del {fecha_real})."
        }
