# main_graph.py

import os
import re
import json
from dotenv import load_dotenv
from typing import Optional
from typing_extensions import TypedDict

import pandas as pd
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableLambda
from langchain_groq import ChatGroq

from prompts import PROMPT_SERIES, PROMPT_DOCUMENTOS, PROMPT_API_EXTRAER
from cotizaciones import construir_respuesta_yfinance
from series_model import ejecutar_prediccion

# ---------------------------------------------------------
# 1. Configuración del modelo (Groq con Mixtral)
# ---------------------------------------------------------

load_dotenv()  # Carga las variables de entorno desde .env

llm = ChatGroq(
    groq_api_key=os.getenv("GROQ_API_KEY"),
    model_name="mixtral-8x7b-32768",
    temperature=0.0
)

# ---------------------------------------------------------
# 2. Función auxiliar para extraer JSON desde texto
# ---------------------------------------------------------

def extract_json(text: str) -> dict:
    try:
        json_text = re.search(r"\{.*\}", text, re.DOTALL).group()
        return json.loads(json_text)
    except Exception as e:
        raise ValueError(f"Error al extraer JSON: {e}\nTexto recibido:\n{text}")

# ---------------------------------------------------------
# 3. Definición del estado del chatbot
# ---------------------------------------------------------

class ChatbotState(TypedDict):
    input: str
    empresa: Optional[str]
    tipo_pregunta: Optional[str]
    respuesta: Optional[str]
    fuente: Optional[str]
    fecha_inicio: Optional[str]
    fecha_fin: Optional[str]

# ---------------------------------------------------------
# 4. Nodo: Clasifica el tipo de pregunta
# ---------------------------------------------------------

def clasificar_intencion(state: ChatbotState) -> ChatbotState:
    pregunta = state["input"].lower()

    if "cotización" in pregunta or "histórico" in pregunta or "rendimiento" in pregunta:
        tipo = "series_temporales"
    elif "informe" in pregunta or "beneficio" in pregunta or "memoria" in pregunta:
        tipo = "documentos_financieros"
    elif "predice" in pregunta or ("en" in pregunta and "días" in pregunta):
        tipo = "series_reales"
    elif "precio actual" in pregunta or "valor ahora" in pregunta or "api" in pregunta or "precio medio" in pregunta:
        tipo = "consulta_api"
    else:
        tipo = "consulta_api"

    return {**state, "tipo_pregunta": tipo}

# ---------------------------------------------------------
# 5. Nodo intermedio: decide la fuente a usar
# ---------------------------------------------------------

def seleccionar_fuente(state: ChatbotState) -> str:
    return state["tipo_pregunta"]

# ---------------------------------------------------------
# 6. Nodo: Simulación de análisis de series temporales
# ---------------------------------------------------------

def analizar_series_temporales(state: ChatbotState) -> ChatbotState:
    prompt = PROMPT_SERIES.format(pregunta=state["input"])
    response = llm.invoke(prompt)
    data = extract_json(response.content)
    return {**state, "respuesta": data["respuesta"], "fuente": "series_temporales"}

# ---------------------------------------------------------
# 7. Nodo: Simulación de documentos financieros
# ---------------------------------------------------------

def extraer_documento_financiero(state: ChatbotState) -> ChatbotState:
    prompt = PROMPT_DOCUMENTOS.format(pregunta=state["input"])
    response = llm.invoke(prompt)
    data = extract_json(response.content)
    return {**state, "respuesta": data["respuesta"], "fuente": "documentos"}

# ---------------------------------------------------------
# 8. Nodo: Llama a yfinance después de extraer datos con el LLM
# ---------------------------------------------------------

def consultar_api_financiera(state: ChatbotState) -> ChatbotState:
    pregunta = state["input"]

    # Paso 1: extraer parámetros con el LLM
    extraction_prompt = PROMPT_API_EXTRAER.format(pregunta=pregunta)
    response = llm.invoke(extraction_prompt)
    data = extract_json(response.content)

    empresa = data.get("empresa")
    fecha_inicio = data.get("fecha_inicio")
    fecha_fin = data.get("fecha_fin")

    if not all([empresa, fecha_inicio, fecha_fin]):
        return {**state, "respuesta": "No se pudieron extraer los parámetros necesarios para consultar los datos.", "fuente": "api"}

    # Paso 2: consultar yfinance
    resultado = construir_respuesta_yfinance(empresa, fecha_inicio, fecha_fin)
    return {
        **state,
        "respuesta": resultado["respuesta"],
        "fuente": "api",
        "empresa": empresa,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin
    }

# ---------------------------------------------------------
# 9. Nodo: Llama al modelo real de series temporales
# ---------------------------------------------------------

def nodo_series_reales(state: ChatbotState) -> ChatbotState:
    # Por ahora hardcodeado, se puede mejorar con extracción dinámica
    empresa = "BBVA"
    lag = 7

    modelos_dir = "./modelos_por_empresa"
    path_csv = "./data/IBEX35_cotizaciones_20_Limpio.csv"

    resultado = ejecutar_prediccion(empresa, lag, path_csv, modelos_dir)

    return {
        **state,
        "respuesta": resultado["respuesta"],
        "fuente": "series_reales"
    }

# ---------------------------------------------------------
# 10. Construcción del grafo LangGraph
# ---------------------------------------------------------

def build_graph():
    graph = StateGraph(ChatbotState)

    graph.add_node("clasificar", RunnableLambda(clasificar_intencion))
    graph.add_node("seleccionar_fuente", RunnableLambda(seleccionar_fuente))
    graph.add_node("series_temporales", RunnableLambda(analizar_series_temporales))
    graph.add_node("documentos_financieros", RunnableLambda(extraer_documento_financiero))
    graph.add_node("consulta_api", RunnableLambda(consultar_api_financiera))
    graph.add_node("series_reales", RunnableLambda(nodo_series_reales))

    graph.set_entry_point("clasificar")
    graph.add_edge("clasificar", "seleccionar_fuente")

    graph.add_conditional_edges("seleccionar_fuente", seleccionar_fuente, {
        "series_temporales": "series_temporales",
        "documentos_financieros": "documentos_financieros",
        "consulta_api": "consulta_api",
        "series_reales": "series_reales"
    })

    graph.add_edge("series_temporales", END)
    graph.add_edge("documentos_financieros", END)
    graph.add_edge("consulta_api", END)
    graph.add_edge("series_reales", END)

    return graph.compile()
