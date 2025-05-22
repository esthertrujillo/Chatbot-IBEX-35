import yfinance as yf

# Ticker de Iberdrola en Yahoo Finance
ticker = "IBE.MC"
fecha_inicio = "2023-03-01"
fecha_fin = "2023-03-31"

df = yf.download(ticker, start=fecha_inicio, end=fecha_fin, progress=False)

if df.empty:
    print("⚠️ No se obtuvieron datos. Verifica el ticker o las fechas.")
else:
    precio_medio = round(df["Close"].mean(), 2)
    print(f"✅ Precio medio de {ticker} entre {fecha_inicio} y {fecha_fin}: {precio_medio}€")
    print(df.head())
