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

# ---------------------------------------------------------
# 1. Configuración del modelo (Groq con Mixtral)
# ---------------------------------------------------------

load_dotenv()  # Carga las variables de entorno desde .env

llm = ChatGroq(
    groq_api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama3-8b-8192",  # ✅ nuevo modelo recomendado
    temperature=0.0
)

# ---------------------------------------------------------
# 2. Función auxiliar para extraer JSON desde texto
# ---------------------------------------------------------

def extract_json(text: str) -> dict:
    try:
        # Limpieza previa
        text = text.strip()

        # Si falta la llave de cierre, intenta agregarla (corrección rápida)
        if text.startswith("{") and not text.endswith("}"):
            text += "}"

        # Intentar parsear directamente
        return json.loads(text)
    except Exception as e:
        raise ValueError(f"❌ Error al extraer JSON: {e}\nTexto recibido:\n{text}")

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

    llm_response_content = response.content.strip()

    print(f"🔍 DEBUG - Respuesta bruta del LLM (strippeada): '{llm_response_content}'")
    print(f"🔍 DEBUG - Tipo de respuesta bruta: {type(llm_response_content)}")

    # AÑADE ESTA LÍNEA TEMPORALMENTE PARA VER EL CONTENIDO DIRECTO
    print(f"🔍 DEBUG - Contenido que se pasa a extract_json: '{llm_response_content}'")

    try:
        data = extract_json(llm_response_content)
    except Exception as e:
        return {
            **state,
            "respuesta": f"❌ No se pudo extraer un JSON válido de la respuesta del LLM. Error: {str(e)}\nRespuesta del LLM (final): '{llm_response_content}'",
            "fuente": "api"
        }

    empresa = data.get("empresa")
    fecha_inicio = data.get("fecha_inicio")
    fecha_fin = data.get("fecha_fin")

    if not all([empresa, fecha_inicio, fecha_fin]):
        return {
            **state,
            "respuesta": "❌ No se pudieron extraer los parámetros necesarios para consultar los datos.",
            "fuente": "api"
        }

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
# 9. Construcción del grafo LangGraph
# ---------------------------------------------------------
def build_graph():
    graph = StateGraph(ChatbotState)

    # Nodos válidos (todos devuelven un dict)
    graph.add_node("clasificar", RunnableLambda(clasificar_intencion))
    graph.add_node("series_temporales", RunnableLambda(analizar_series_temporales))
    graph.add_node("documentos_financieros", RunnableLambda(extraer_documento_financiero))
    graph.add_node("consulta_api", RunnableLambda(consultar_api_financiera))

    # Punto de entrada
    graph.set_entry_point("clasificar")

    # Enrutamiento condicional desde el nodo 'clasificar'
    graph.add_conditional_edges("clasificar", seleccionar_fuente, {
        "series_temporales": "series_temporales",
        "documentos_financieros": "documentos_financieros",
        "consulta_api": "consulta_api"
    })

    # Todos los nodos terminales
    graph.add_edge("series_temporales", END)
    graph.add_edge("documentos_financieros", END)
    graph.add_edge("consulta_api", END)

    return graph.compile()
