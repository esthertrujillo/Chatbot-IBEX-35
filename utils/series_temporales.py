import pandas as pd 
import matplotlib.pyplot as plt
import os
from io import BytesIO
import base64
import re
import pickle

# -------------------------------
# 📦 Cargar modelo entrenado
# -------------------------------
def cargar_modelo_lag(empresa: str, lag: int):
    nombre_archivo = f"{empresa.upper()}_lag{lag}.pkl"
    ruta = os.path.join("modelos_por_empresa", nombre_archivo)
    if not os.path.exists(ruta):
        raise FileNotFoundError(f"No se encontró el archivo {ruta}")
    with open(ruta, "rb") as f:
        return pickle.load(f)

# -------------------------------
# 📈 Generar gráfico de predicciones
# -------------------------------
def generar_grafico_predicciones(df: pd.DataFrame, empresa: str, lag: int, modelo) -> str:
    X = df[[f"lag_{i}" for i in range(1, lag + 1)]]
    y_true = df["target"]
    y_pred = modelo.predict(X)

    plt.figure(figsize=(10, 4))
    plt.plot(df.index, y_true, label="Real", linestyle="--")
    plt.plot(df.index, y_pred, label="Predicción", linewidth=2)
    plt.title(f"Predicción de precios para {empresa} con lag {lag}")
    plt.xlabel("Fecha")
    plt.ylabel("Precio")
    plt.legend()
    plt.tight_layout()

    buffer = BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.read()).decode("utf-8")
    plt.close()

    return img_base64

# -------------------------------
# 🏦 Lista de empresas del IBEX 35
# -------------------------------
EMPRESAS_IBEX = [
    'ACCIONA', 'ACCIONA ENERGÍA', 'ACERINOX', 'ACS', 'AENA', 'AMADEUS', 'ARCELORMITTAL',
    'BANKINTER', 'BBVA', 'CAIXABANK', 'CELLNEX TELECOM', 'ENAGAS', 'ENDESA', 'FERROVIAL',
    'FLUIDRA', 'GRIFOLS', 'IAG', 'IBERDROLA', 'INDITEX', 'INDRA', 'INM. COLONIAL',
    'LABORATORIOS FARMA (ROVI)', 'LOGISTA', 'MAPFRE', 'MERLIN PROPERTIES', 'NATURGY',
    'PUIG', 'REE', 'REPSOL', 'SABADELL', 'SACYR', 'SANTANDER', 'SOLARIA ENERGIA',
    'TELEFONICA', 'UNICAJA BANCO'
]

# -------------------------------
# 🔎 Detección de empresa en texto
# -------------------------------
def detectar_empresa(pregunta: str) -> str:
    pregunta_lower = pregunta.lower()
    for empresa in EMPRESAS_IBEX:
        if empresa.lower() in pregunta_lower:
            return empresa.upper()
    return "IBERDROLA"  # por defecto

# -------------------------------
# ⏳ Detección de lag en texto
# -------------------------------
def detectar_lag(pregunta: str) -> int:
    pregunta_lower = pregunta.lower()
    if re.search(r"ayer|últim[oa] sesión|últim[oa] jornada", pregunta_lower):
        return 1
    if re.search(r"últim[oa] semana|7 días|siete días", pregunta_lower):
        return 7
    if re.search(r"15 días|quince días|dos semanas", pregunta_lower):
        return 15
    return 7  # por defecto
