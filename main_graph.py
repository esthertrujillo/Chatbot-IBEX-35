import os
import re
import json
from datetime import datetime, timedelta 
from dotenv import load_dotenv
from typing import Optional
from typing_extensions import TypedDict
import pandas as pd
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableLambda
from langchain_groq import ChatGroq
from prompts import PROMPT_SERIES, PROMPT_DOCUMENTOS, PROMPT_API_EXTRAER, PROMPT_CLASIFICACION, PROMPT_API
from cotizaciones import construir_respuesta_yfinance

# ---------------------------------------------------------
# 1. Configuración del modelo
# ---------------------------------------------------------

load_dotenv()
llm = ChatGroq(
    groq_api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama3-8b-8192",
    temperature=0.0
)

# ---------------------------------------------------------
# 2. Estado del chatbot
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
# 3. Funciones auxiliares y utilidades
# ---------------------------------------------------------

### 1. Extrae un JSON del texto dado, manejando errores y formatos incorrectos

def extract_json(text: str) -> dict:
    try:
        text = text.strip()
        if text.startswith("{") and not text.endswith("}"):
            text += "}"
        return json.loads(text)
    except Exception as e:
        raise ValueError(f"❌ Error al extraer JSON: {e}\nTexto recibido:\n{text}")

### 2. Normaliza fechas relativas como "lunes pasado" a la fecha del último lunes
def normalizar_fechas_relativas(fecha_inicio, fecha_fin):
    hoy = datetime.today()
    
    def get_last_monday():
        return hoy - timedelta(days=hoy.weekday() + 7)

    def to_str(date_obj):
        return date_obj.strftime("%Y-%m-%d")
    
    if fecha_inicio is None or "lunes pasado" in fecha_inicio.lower():
        fecha_inicio = to_str(get_last_monday())
    if fecha_fin is None or "lunes pasado" in fecha_fin.lower():
        fecha_fin = to_str(get_last_monday())

    return fecha_inicio, fecha_fin



# ---------------------------------------------------------
# 4. Nodo: Clasificación
# ---------------------------------------------------------

def clasificar_intencion(state: ChatbotState) -> ChatbotState:
    prompt = PROMPT_CLASIFICACION.format(pregunta=state["input"])
    respuesta = llm.invoke(prompt).content.strip().lower()
    categorias_validas = {"series_temporales", "documentos_financieros", "consulta_api"}
    tipo = respuesta if respuesta in categorias_validas else "consulta_api"
    
    print(f"[🔍 CLASIFICADOR] Pregunta: {state['input']}")
    print(f"[🔍 CLASIFICADOR] Prompt enviado:\n{prompt}")
    print(f"[🔍 CLASIFICADOR] Respuesta del modelo: {respuesta}")
    print(f"[🔍 CLASIFICADOR] Tipo detectado: {tipo}")

    return {**state, "tipo_pregunta": tipo, "fuente": "clasificador"}

# ---------------------------------------------------------
# 5. Nodo de decisión
# ---------------------------------------------------------

def seleccionar_fuente(state: ChatbotState) -> str:
    return state["tipo_pregunta"]

# ---------------------------------------------------------
# 6. Nodo: Series temporales
# ---------------------------------------------------------

def analizar_series_temporales(state: ChatbotState) -> ChatbotState:
    print(f"[🟦 Nodo SERIES] Pregunta: {state['input']}")
    prompt = PROMPT_SERIES.format(pregunta=state["input"])
    print(f"[🟦 Nodo SERIES] Prompt enviado:\n{prompt}")
    
    response = llm.invoke(prompt)
    print(f"[🟦 Nodo SERIES] Respuesta del modelo:\n{response.content}")
    
    data = extract_json(response.content)
    return {**state, "respuesta": data["respuesta"], "fuente": "series_temporales"}

# ---------------------------------------------------------
# 7. Nodo: Documentos financieros
# ---------------------------------------------------------

def extraer_documento_financiero(state: ChatbotState) -> ChatbotState:
    print(f"[📊 Nodo DOCUMENTOS] Pregunta: {state['input']}")
    prompt = PROMPT_DOCUMENTOS.format(pregunta=state["input"])
    print(f"[📊 Nodo DOCUMENTOS] Prompt enviado:\n{prompt}")
    
    response = llm.invoke(prompt)
    print(f"[📊 Nodo DOCUMENTOS] Respuesta del modelo:\n{response.content}")
    
    data = extract_json(response.content)
    return {**state, "respuesta": data["respuesta"], "fuente": "documentos"}

# ---------------------------------------------------------
# 8. Nodo: Consulta API financiera
# ---------------------------------------------------------
def consultar_api_financiera(state: ChatbotState) -> ChatbotState:
    pregunta = state["input"]
    print(f"[🌐 Nodo API] Pregunta: {pregunta}")
    
    # Paso 1: extracción de parámetros
    extraction_prompt = PROMPT_API_EXTRAER.format(pregunta=pregunta)
    response = llm.invoke(extraction_prompt)
    llm_response_content = response.content.strip()
    print(f"[🌐 Nodo API] Prompt extracción:\n{extraction_prompt}")
    print(f"[🌐 Nodo API] Respuesta LLM para extracción:\n{llm_response_content}")

    try:
        data = extract_json(llm_response_content)
        empresa = data.get("empresa")
        fecha_inicio = data.get("fecha_inicio")
        fecha_fin = data.get("fecha_fin")

        # ✅ Normaliza si pone "lunes pasado" u otras expresiones
        fecha_inicio, fecha_fin = normalizar_fechas_relativas(fecha_inicio, fecha_fin)

    except Exception as e:
        print(f"⚠️ Error extrayendo parámetros: {e}")
        return {
            **state,
            "respuesta": "❌ No se pudieron extraer los parámetros necesarios para consultar los datos.",
            "fuente": "api"
        }

    print(f"[🌐 Nodo API] Parámetros extraídos: empresa={empresa}, desde={fecha_inicio}, hasta={fecha_fin}")

    if not all([empresa, fecha_inicio, fecha_fin]):
        return {
            **state,
            "respuesta": "❌ Faltan parámetros clave: empresa, fecha de inicio o fin.",
            "fuente": "api"
        }

    # Paso 2: simulación con PROMPT_API
    simulacion_prompt = PROMPT_API.format(pregunta=pregunta)
    simulacion_response = llm.invoke(simulacion_prompt)
    print(f"[🌐 Nodo API] Prompt de simulación:\n{simulacion_prompt}")
    print(f"[🌐 Nodo API] Respuesta simulada:\n{simulacion_response.content}")

    try:
        data_simulada = extract_json(simulacion_response.content)
        respuesta_simulada = data_simulada.get("respuesta", "(El LLM no devolvió una clave 'respuesta')")
    except Exception as e:
        print(f"⚠️ Error extrayendo respuesta simulada: {e}")
        respuesta_simulada = "(No se pudo generar una respuesta simulada del LLM)"

    # Paso 3: llamada real a yfinance
    resultado = construir_respuesta_yfinance(empresa, fecha_inicio, fecha_fin)
    print(f"[🌐 Nodo API] Respuesta real:\n{resultado['respuesta']}")

    # Paso 4: combinación
    respuesta_final = f"{respuesta_simulada}\n\n📊 Datos reales:\n{resultado['respuesta']}"

    return {
        **state,
        "respuesta": respuesta_final,
        "fuente": "api",
        "empresa": empresa,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin
    }


# ---------------------------------------------------------
# 9. Construcción del grafo
# ---------------------------------------------------------

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

graph = build_graph()
