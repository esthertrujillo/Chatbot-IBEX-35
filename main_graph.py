# main_graph.py

import os
import json
from dotenv import load_dotenv
from typing import Optional
from typing_extensions import TypedDict
from datetime import date, timedelta

import pandas as pd
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableLambda
from langchain_groq import ChatGroq

from prompts import PROMPT_SERIES, PROMPT_DOCUMENTOS, PROMPT_API_EXTRAER
from cotizaciones import construir_respuesta_yfinance

# Fecha actual y de ayer para prompts
HOY = date.today()
AYER = HOY - timedelta(days=1)

# 1. Configuración del modelo (Groq con Mixtral)
load_dotenv()
llm = ChatGroq(
    groq_api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama3-8b-8192",
    temperature=0.0
)

# 2. Función auxiliar para extraer JSON
def extract_json(text: str) -> dict:
    try:
        text = text.strip()
        if text.startswith("{") and not text.endswith("}"):
            text += "}"
        return json.loads(text)
    except Exception as e:
        raise ValueError(f"❌ Error al extraer JSON: {e}\nTexto recibido:\n{text}")

# 3. Estado del chatbot
class ChatbotState(TypedDict):
    input: str
    empresa: Optional[str]
    tipo_pregunta: Optional[str]
    respuesta: Optional[str]
    fuente: Optional[str]
    fecha_inicio: Optional[str]
    fecha_fin: Optional[str]
    fecha_real: Optional[str]  # ← añadido

# 4. Clasifica intención
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
    print(f"📍 Nodo: clasificar_intencion → tipo detectado: {tipo}")
    return {**state, "tipo_pregunta": tipo}

# 5. Decide nodo según tipo
def seleccionar_fuente(state: ChatbotState) -> str:
    return state["tipo_pregunta"]

# 6. Nodo series temporales
def analizar_series_temporales(state: ChatbotState) -> ChatbotState:
    prompt = PROMPT_SERIES.format(pregunta=state["input"])
    print(f"\n📤 PROMPT SERIES TEMPORALES:\n{prompt}")
    response = llm.invoke(prompt)
    print(f"📥 RESPUESTA LLM:\n{response.content}")
    data = extract_json(response.content)
    return {**state, "respuesta": data["respuesta"], "fuente": "series_temporales"}

# 7. Nodo documentos financieros
def extraer_documento_financiero(state: ChatbotState) -> ChatbotState:
    prompt = PROMPT_DOCUMENTOS.format(pregunta=state["input"])
    print(f"\n📤 PROMPT DOCUMENTOS FINANCIEROS:\n{prompt}")
    response = llm.invoke(prompt)
    print(f"📥 RESPUESTA LLM:\n{response.content}")
    data = extract_json(response.content)
    return {**state, "respuesta": data["respuesta"], "fuente": "documentos"}

# 8. Nodo API financiera (yfinance)
def consultar_api_financiera(state: ChatbotState) -> ChatbotState:
    pregunta = state["input"]

    # 🗓️ Fechas relativas calculadas dinámicamente
    HOY = date.today()
    AYER = HOY - timedelta(days=1)
    HOY_MENOS_7 = HOY - timedelta(days=7)

    # 🧠 Construcción del prompt usando todas las fechas
    extraction_prompt = PROMPT_API_EXTRAER.format(
        pregunta=pregunta,
        hoy=HOY.strftime("%Y-%m-%d"),
        ayer=AYER.strftime("%Y-%m-%d"),
        hoy_menos_7=HOY_MENOS_7.strftime("%Y-%m-%d")
    )

    print(f"\n📤 PROMPT API_EXTRAER:\n{extraction_prompt}")
    response = llm.invoke(extraction_prompt)
    llm_response_content = response.content.strip()
    print(f"📥 RESPUESTA LLM (raw):\n{llm_response_content}")

    try:
        data = extract_json(llm_response_content)
    except Exception as e:
        return {
            **state,
            "respuesta": f"❌ No se pudo extraer JSON. Error: {str(e)}\nContenido recibido: {llm_response_content}",
            "fuente": "api"
        }

    empresa = data.get("empresa")
    fecha_inicio = data.get("fecha_inicio")
    fecha_fin = data.get("fecha_fin")

    print(f"✅ PARÁMETROS EXTRAÍDOS → Empresa: {empresa}, Desde: {fecha_inicio}, Hasta: {fecha_fin}")

    if not all([empresa, fecha_inicio, fecha_fin]):
        return {
            **state,
            "respuesta": "❌ Faltan parámetros clave para la consulta.",
            "fuente": "api"
        }

    resultado = construir_respuesta_yfinance(empresa, fecha_inicio, fecha_fin)
    print(f"📊 RESPUESTA FINAL YFINANCE:\n{resultado['respuesta']}")

    return {
        **state,
        "respuesta": resultado["respuesta"],
        "fuente": "api",
        "empresa": empresa,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "fecha_real": resultado.get("fecha_real")  # opcional
    }
# 9. Construcción del grafo
def build_graph():
    graph = StateGraph(ChatbotState)
    graph.add_node("clasificar", RunnableLambda(clasificar_intencion))
    graph.add_node("series_temporales", RunnableLambda(analizar_series_temporales))
    graph.add_node("documentos_financieros", RunnableLambda(extraer_documento_financiero))
    graph.add_node("consulta_api", RunnableLambda(consultar_api_financiera))

    graph.set_entry_point("clasificar")
    graph.add_conditional_edges("clasificar", seleccionar_fuente, {
        "series_temporales": "series_temporales",
        "documentos_financieros": "documentos_financieros",
        "consulta_api": "consulta_api"
    })

    graph.add_edge("series_temporales", END)
    graph.add_edge("documentos_financieros", END)
    graph.add_edge("consulta_api", END)

    return graph.compile()
