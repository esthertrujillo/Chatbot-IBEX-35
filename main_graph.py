import os
import re
import json
from datetime import datetime, timedelta 
from dotenv import load_dotenv
from typing import Optional
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableLambda
from langchain_groq import ChatGroq

from qdrant_utils import buscar_en_qdrant
from prompts import PROMPT_SERIES, PROMPT_API_EXTRAER, PROMPT_CLASIFICACION, PROMPT_API, PROMPT_RAG_DOCUMENTOS
from cotizaciones import construir_respuesta_yfinance
from series_model import ejecutar_prediccion

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
        # Buscar el bloque de JSON en el texto
        matches = re.findall(r"\{.*?\}", text, re.DOTALL)  # Buscar todo lo que parece un JSON
        if not matches:
            raise ValueError("No se encontró un bloque JSON en el texto.")
        
        # El primer bloque encontrado se considera el JSON
        json_text = matches[0]
        
        # Intentamos cargar el JSON
        return json.loads(json_text)
    except Exception as e:
        raise ValueError(f"Error al extraer JSON: {e}\nTexto recibido:\n{text}")

def normalizar_fechas_relativas(fecha_inicio, fecha_fin):
    hoy_dt = datetime.today() # Renombrado para evitar conflicto con la cadena 'hoy'

    def get_last_monday(date_ref):
        # Calculate last Monday relative to the reference date
        return date_ref - timedelta(days=date_ref.weekday()) - timedelta(days=7)

    def to_str(date_obj):
        return date_obj.strftime("%Y-%m-%d")

    # Handle fecha_inicio
    if fecha_inicio:
        fecha_inicio_lower = fecha_inicio.lower()
        if "lunes pasado" in fecha_inicio_lower:
            fecha_inicio = to_str(get_last_monday(hoy_dt))
        elif "hoy" in fecha_inicio_lower:
            fecha_inicio = to_str(hoy_dt)
        # Add more relative date handling here if needed
        # elif "ayer" in fecha_inicio_lower:
        #     fecha_inicio = to_str(hoy_dt - timedelta(days=1))
        # elif "esta semana" in fecha_inicio_lower:
        #     fecha_inicio = to_str(hoy_dt - timedelta(days=hoy_dt.weekday())) # Monday of current week

    # Handle fecha_fin
    if fecha_fin:
        fecha_fin_lower = fecha_fin.lower()
        if "lunes pasado" in fecha_fin_lower:
            fecha_fin = to_str(get_last_monday(hoy_dt))
        elif "hoy" in fecha_fin_lower:
            fecha_fin = to_str(hoy_dt)
        # Add more relative date handling here if needed
        # elif "ayer" in fecha_fin_lower:
        #     fecha_fin = to_str(hoy_dt - timedelta(days=1))
        # elif "esta semana" in fecha_fin_lower:
        #     fecha_fin = to_str(hoy_dt + timedelta(days=6 - hoy_dt.weekday())) # Sunday of current week


    # If dates are still not normalized (e.g., they were specific dates like "2022-04-01")
    # You might want to add validation here to ensure they are in the correct format
    # or attempt to parse them. For example:
    if fecha_inicio and not re.match(r"\d{4}-\d{2}-\d{2}", fecha_inicio):
        try:
            # Attempt to parse if it's not a relative term but also not in YYYY-MM-DD
            parsed_date = datetime.strptime(fecha_inicio, "%Y-%m-%d") # Or other expected formats
            fecha_inicio = to_str(parsed_date)
        except ValueError:
            print(f"Advertencia: No se pudo normalizar fecha_inicio: {fecha_inicio}")
            # Optionally set to None or a default if parsing fails
            fecha_inicio = None # Or raise an error
            # If you expect the LLM to provide YYYY-MM-DD, this might indicate an LLM issue

    if fecha_fin and not re.match(r"\d{4}-\d{2}-\d{2}", fecha_fin):
        try:
            parsed_date = datetime.strptime(fecha_fin, "%Y-%m-%d")
            fecha_fin = to_str(parsed_date)
        except ValueError:
            print(f"Advertencia: No se pudo normalizar fecha_fin: {fecha_fin}")
            fecha_fin = None


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

## ---------------------------------------------------------
# 6. Nodo: Series temporales
# ---------------------------------------------------------

def analizar_series_temporales(state: ChatbotState) -> ChatbotState:
    pregunta = state["input"]

    # Formatear el prompt con la pregunta del usuario
    prompt = PROMPT_SERIES.format(pregunta=pregunta)
    response = llm.invoke(prompt)
    try:
        # Extraer la información en formato JSON
        data = extract_json(response.content)
    except Exception as e:
        print(f"⚠️ Error extrayendo JSON del LLM: {e}")
        return {
            **state,
            "respuesta": "❌ No se pudo extraer la información de la pregunta.",
            "fuente": "series_temporales"
        }

    # Obtener la empresa, el lag y la respuesta simulada
    empresa = data.get("empresa", "BBVA").upper()
    lag = int(data.get("lag", 1))
    respuesta_simulada = data.get("respuesta", "")

    print(f"[📊 SERIES] Empresa detectada: {empresa}, lag: {lag}")
    print(f"[📊 SERIES] Respuesta simulada: {respuesta_simulada}")

    # Aquí, si lo deseas, puedes incluir la predicción real basada en tus modelos.
    # Los pasos adicionales para obtener la predicción real podrían seguir siendo relevantes
    modelos_dir = os.path.join(os.getcwd(), "modelos_por_empresa")
    path_csv = os.path.join(os.getcwd(), "IBEX35_cotizaciones_20_Limpio.csv")

    # Llamar al modelo para obtener la predicción real (si es necesario)
    resultado = ejecutar_prediccion(empresa, lag, path_csv, modelos_dir)
    respuesta_modelo = resultado.get("respuesta", "No se pudo obtener la predicción real.")

    # Devolver la respuesta final sin detalles adicionales como RMSE
    return {
        **state,
        "respuesta": f"{respuesta_simulada}",  # Solo la respuesta simulada
        "fuente": "series_temporales",
        "empresa": empresa
    }


# ---------------------------------------------------------
# 7. Nodo: Documentos financieros -> Qdrant
# ---------------------------------------------------------

def consulta_qdrant(state: ChatbotState) -> ChatbotState:
    pregunta = state["input"]
    
    resultados = buscar_en_qdrant(pregunta)
    fragmentos = [r.payload.get("fragmento", "") for r in resultados]
    contexto = "\n\n".join(fragmentos)

    prompt_rag = PROMPT_RAG_DOCUMENTOS.format(contexto=contexto, pregunta=pregunta)
    respuesta_llm = llm.invoke(prompt_rag).content.strip()

    try:
        data = extract_json(respuesta_llm)
        respuesta_final = data.get("respuesta", "(El modelo no devolvió una clave 'respuesta').")
    except Exception as e:
        print(f"⚠️ Error extrayendo JSON del LLM: {e}")
        respuesta_final = respuesta_llm

    respuesta_final = respuesta_final.replace(". ", ".  \n").replace("- ", "• ")

    return {
        **state,
        "respuesta": respuesta_final,
        "fuente": "qdrant",
        "fragmentos": fragmentos
    }

# ---------------------------------------------------------
# 8. Nodo: Consulta API financiera
# ---------------------------------------------------------

def consultar_api_financiera(state: ChatbotState) -> ChatbotState:
    pregunta = state["input"]
    print(f"[🌐 Nodo API] Pregunta: {pregunta}")
    
    # Extraer parámetros desde el LLM
    extraction_prompt = PROMPT_API_EXTRAER.format(pregunta=pregunta)
    print(f"[🌐 Nodo API] Prompt de extracción:\n{extraction_prompt}")
    
    response = llm.invoke(extraction_prompt)
    llm_response_content = response.content.strip()
    
    print(f"[🌐 Nodo API] Respuesta LLM para extracción CRUDA:\n'{llm_response_content}'")
    
    try:
        # Extraer datos del JSON
        data = extract_json(llm_response_content)
        print(f"[🌐 Nodo API] Datos extraídos del LLM:\n{data}")

        # Normalizar el nombre de la empresa
        empresa = data.get("empresa")
        if not empresa:
            print("⚠️ No se pudo extraer la empresa del JSON")
        empresa_normalizada = empresa.strip().lower() if empresa else None  # Normalizar a minúsculas y quitar espacios
        print(f"[🌐 Nodo API] Empresa normalizada: {empresa_normalizada}")
        
        # Verificar que las fechas sean válidas
        fecha_inicio = data.get("fecha_inicio")
        fecha_fin = data.get("fecha_fin")
        fecha_inicio, fecha_fin = normalizar_fechas_relativas(fecha_inicio, fecha_fin)
        print(f"[🌐 Nodo API] Fechas normalizadas: {fecha_inicio}, {fecha_fin}")

    except Exception as e:
        print(f"⚠️ Error extrayendo parámetros: {e}")
        return {
            **state,
            "respuesta": "❌ No se pudieron extraer los parámetros necesarios para consultar los datos.",
            "fuente": "api"
        }

    # Validación de los parámetros clave
    if not all([empresa_normalizada, fecha_inicio, fecha_fin]):
        print(f"⚠️ Faltan parámetros clave: empresa={empresa_normalizada}, fecha_inicio={fecha_inicio}, fecha_fin={fecha_fin}")
        return {
            **state,
            "respuesta": "❌ Faltan parámetros clave: empresa, fecha de inicio o fin.",
            "fuente": "api"
        }

    # Generación del prompt para simulación
    simulacion_prompt = PROMPT_API.format(pregunta=pregunta)
    print(f"[🌐 Nodo API] Prompt de simulación:\n{simulacion_prompt}")
    
    simulacion_response = llm.invoke(simulacion_prompt)
    print(f"[🌐 Nodo API] Respuesta simulada:\n{simulacion_response.content}")

    try:
        # Extraer la respuesta simulada
        data_simulada = extract_json(simulacion_response.content)
        respuesta_simulada = data_simulada.get("respuesta", "(El LLM no devolvió una clave 'respuesta')")
        print(f"[🌐 Nodo API] Respuesta simulada extraída: {respuesta_simulada}")
    except Exception as e:
        print(f"⚠️ Error extrayendo respuesta simulada: {e}")
        respuesta_simulada = "(No se pudo generar una respuesta simulada del LLM)"

    # Obtener los datos reales de la API financiera
    resultado = construir_respuesta_yfinance(empresa_normalizada, fecha_inicio, fecha_fin)
    print(f"[🌐 Nodo API] Resultado de la API financiera:\n{resultado['respuesta']}")

    # Combina la respuesta simulada con los datos reales
    respuesta_final = f"{respuesta_simulada}\n\n📊 Datos reales:\n{resultado['respuesta']}"
    print(f"[🌐 Nodo API] Respuesta final combinada:\n{respuesta_final}")

    return {
        **state,
        "respuesta": respuesta_final,
        "fuente": "api",
        "empresa": empresa_normalizada,
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
    graph.add_node("consulta_qdrant", RunnableLambda(consulta_qdrant))
    graph.add_node("consulta_api", RunnableLambda(consultar_api_financiera))

    graph.set_entry_point("clasificar")

    graph.add_conditional_edges("clasificar", seleccionar_fuente, {
        "series_temporales": "series_temporales",
        "documentos_financieros": "consulta_qdrant",
        "consulta_api": "consulta_api"
    })

    graph.add_edge("series_temporales", END)
    graph.add_edge("consulta_qdrant", END)
    graph.add_edge("consulta_api", END)

    return graph.compile()

# Compilamos el grafo
graph = build_graph()
