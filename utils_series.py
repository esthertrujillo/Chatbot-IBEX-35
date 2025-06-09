import pandas as pd
import matplotlib.pyplot as plt
import os
from io import BytesIO
import base64
import re

# Cargar el archivo .pkl con los datos de la empresa y el lag correspondiente
def cargar_datos_lag(empresa: str, lag: int) -> pd.DataFrame:
    nombre_archivo = f"{empresa.upper()}_lag{lag}.pkl"
    ruta = os.path.join("modelos_por_empresa", nombre_archivo)
    if not os.path.exists(ruta):
        raise FileNotFoundError(f"No se encontró el archivo {ruta}")
    return pd.read_pickle(ruta)

# Generar gráfico y devolver imagen como base64
def generar_grafico_predicciones(df: pd.DataFrame, empresa: str, lag: int) -> str:
    fig, ax = plt.subplots(figsize=(10, 4))
    df.plot(ax=ax)
    ax.set_title(f"Predicciones para {empresa} con lag = {lag}")
    ax.set_xlabel("Índice / Tiempo")
    ax.set_ylabel("Precio estimado")
    plt.xticks(rotation=45)
    plt.tight_layout()

    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    plt.close(fig)
    return img_base64

# Lista de empresas reales del dataset IBEX
EMPRESAS_IBEX = [
    'ACCIONA',
    'ACCIONA ENERGÍA',
    'ACERINOX',
    'ACS',
    'AENA',
    'AMADEUS',
    'ARCELORMITTAL',
    'BANKINTER',
    'BBVA',
    'CAIXABANK',
    'CELLNEX TELECOM',
    'ENAGAS',
    'ENDESA',
    'FERROVIAL',
    'FLUIDRA',
    'GRIFOLS',
    'IAG',
    'IBERDROLA',
    'INDITEX',
    'INDRA',
    'INM. COLONIAL',
    'LABORATORIOS FARMA (ROVI)',
    'LOGISTA',
    'MAPFRE',
    'MERLIN PROPERTIES',
    'NATURGY',
    'PUIG',
    'REE',
    'REPSOL',
    'SABADELL',
    'SACYR',
    'SANTANDER',
    'SOLARIA ENERGIA',
    'TELEFONICA',
    'UNICAJA BANCO'
]

# Detectar la empresa mencionada en la pregunta
def detectar_empresa(pregunta: str) -> str:
    pregunta_lower = pregunta.lower()
    for empresa in EMPRESAS_IBEX:
        if empresa.lower() in pregunta_lower:
            return empresa.upper()
    return "IBERDROLA"  # valor por defecto

# Detectar el lag basado en expresiones temporales
def detectar_lag(pregunta: str) -> int:
    pregunta_lower = pregunta.lower()
    if re.search(r"ayer|últim[oa] sesión|últim[oa] jornada", pregunta_lower):
        return 1
    if re.search(r"últim[oa] semana|7 días|siete días", pregunta_lower):
        return 7
    if re.search(r"15 días|quince días|dos semanas", pregunta_lower):
        return 15
    return 7  # valor por defecto
