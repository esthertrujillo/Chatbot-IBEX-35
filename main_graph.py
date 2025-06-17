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

from qdrant_utils import buscar_en_qdrant
from prompts import PROMPT_SERIES, PROMPT_API_EXTRAER, PROMPT_CLASIFICACION, PROMPT_API, PROMPT_RAG_DOCUMENTOS
from cotizaciones import construir_respuesta_yfinance
from utils.series_temporales import (
    detectar_empresa,
    detectar_lag,
    cargar_modelo_lag,
    generar_grafico_predicciones
)

# ---------------------------------------------------------
# 1. Configuración del modelo
# ---------------------------------------------------------

load_dotenv()
print("GROQ_API_KEY cargada:", os.getenv("GROQ_API_KEY"))

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
    grafico_base64: Optional[str]

# ---------------------------------------------------------
# 3. Funciones auxiliares
# ---------------------------------------------------------

def extract_json(text: str) -> dict:
    try:
        text = text.strip()
        # Intenta limpiar control chars (por ejemplo \n no escapados)
        text = re.sub(r'(?<!\\)\n', ' ', text)  # Cambia saltos de línea sin escapar por espacio
        if text.startswith("{") and not text.endswith("}"):
            text += "}"
        return json.loads(text)
    except Exception as e:
        raise ValueError(f"❌ Error al extraer JSON: {e}\nTexto recibido:\n{text}")

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
    pregunta = state["input"]
    prompt = PROMPT_SERIES.format(pregunta=pregunta)
    response = llm.invoke(prompt)

    try:
        data = extract_json(response.content)
        respuesta_texto = data["respuesta"]
    except Exception as e:
        respuesta_texto = "(No se pudo interpretar la respuesta del modelo)"
        print(f"⚠️ Error interpretando JSON: {e}")

    empresa = detectar_empresa(pregunta)
    lag = detectar_lag(pregunta)

    try:
        modelo_cargado = cargar_modelo_lag(empresa, lag)
        df = modelo_cargado["data"]
        modelo = modelo_cargado["modelo"]
        img_base64 = generar_grafico_predicciones(df, empresa, lag, modelo)
    except Exception as e:
        img_base64 = None
        print(f"⚠️ Error al generar gráfico para {empresa} con lag {lag}: {e}")

    return {
        **state,
        "respuesta": respuesta_texto,
        "fuente": "series_temporales",
        "empresa": empresa,
        "grafico_base64": img_base64
    }


# ---------------------------------------------------------
# 7. Nodo: Documentos financieros -> Llama a Qdrant
# ---------------------------------------------------------

def consulta_qdrant(state: ChatbotState) -> ChatbotState:
    pregunta = state["input"]
    
    # Buscar fragmentos relevantes en Qdrant
    resultados = buscar_en_qdrant(pregunta)
    fragmentos = [r.payload.get("fragmento", "") for r in resultados]
    contexto = "\n\n".join(fragmentos)

    # Construir el prompt RAG usando el contexto y la pregunta
    prompt_rag = PROMPT_RAG_DOCUMENTOS.format(contexto=contexto, pregunta=pregunta)

    # Invocar el LLM
    respuesta_llm = llm.invoke(prompt_rag).content.strip()

    # Intentar extraer el JSON con la respuesta
    try:
        data = extract_json(respuesta_llm)
        respuesta_final = data.get("respuesta", "(El modelo no devolvió una clave 'respuesta').")
    except Exception as e:
        print(f"⚠️ Error extrayendo JSON del LLM: {e}")
        respuesta_final = respuesta_llm  # fallback: muestra el texto bruto del LLM

    # 👉 APLICAMOS FORMATO
    respuesta_final = respuesta_final.replace(". ", ".  \n")  # salto de línea tras cada punto
    respuesta_final = respuesta_final.replace("- ", "• ")   # cambia guiones por bullets

    # Devolvemos el estado actualizado
    return {
        **state,
        "respuesta": respuesta_final,
        "fuente": "qdrant",
        "fragmentos": fragmentos  # si quieres mostrar los fragmentos en Streamlit
    }

# ---------------------------------------------------------
# 8. Nodo: Consulta API financiera
# ---------------------------------------------------------

def consultar_api_financiera(state: ChatbotState) -> ChatbotState:
    pregunta = state["input"]
    print(f"[🌐 Nodo API] Pregunta: {pregunta}")
    
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
        fecha_inicio, fecha_fin = normalizar_fechas_relativas(fecha_inicio, fecha_fin)
    except Exception as e:
        print(f"⚠️ Error extrayendo parámetros: {e}")
        return {
            **state,
            "respuesta": "❌ No se pudieron extraer los parámetros necesarios para consultar los datos.",
            "fuente": "api"
        }

    if not all([empresa, fecha_inicio, fecha_fin]):
        return {
            **state,
            "respuesta": "❌ Faltan parámetros clave: empresa, fecha de inicio o fin.",
            "fuente": "api"
        }

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

    resultado = construir_respuesta_yfinance(empresa, fecha_inicio, fecha_fin)
    print(f"[🌐 Nodo API] Respuesta real:\n{resultado['respuesta']}")

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

    # Añadimos los nodos
    graph.add_node("clasificar", RunnableLambda(clasificar_intencion))
    graph.add_node("series_temporales", RunnableLambda(analizar_series_temporales))
    graph.add_node("consulta_qdrant", RunnableLambda(consulta_qdrant))
    graph.add_node("consulta_api", RunnableLambda(consultar_api_financiera))

    # Punto de entrada
    graph.set_entry_point("clasificar")

    # Definimos cómo se mueve entre nodos según la clasificación
    graph.add_conditional_edges("clasificar", seleccionar_fuente, {
        "series_temporales": "series_temporales",
        "documentos_financieros": "consulta_qdrant",  # Las preguntas sobre documentos van al nodo Qdrant (RAG)
        "consulta_api": "consulta_api"
    })

    # Finalizamos el flujo en estos nodos
    graph.add_edge("series_temporales", END)
    graph.add_edge("consulta_qdrant", END)
    graph.add_edge("consulta_api", END)

    return graph.compile()

# Compilamos el grafo
graph = build_graph()
