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
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage # Importar para memoria

from qdrant_utils import buscar_en_qdrant
# Importa el nuevo prompt PROMPT_FILTRO_INICIAL
from prompts import PROMPT_SERIES, PROMPT_API_EXTRAER, PROMPT_CLASIFICACION, PROMPT_API, PROMPT_RAG_DOCUMENTOS, PROMPT_FILTRO_INICIAL, PROMPT_DOCUMENTOS
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
    chat_history: list[BaseMessage] # Campo para el historial de chat
    empresa: Optional[str]
    tipo_pregunta: Optional[str]
    respuesta: Optional[str]
    fuente: Optional[str]
    fecha_inicio: Optional[str]
    fecha_fin: Optional[str]
    grafico_base64: Optional[str]
    categoria_inicial: Optional[str] # Nuevo campo para el resultado del filtro inicial

# ---------------------------------------------------------
# 3. Funciones auxiliares
# ---------------------------------------------------------

def extract_json(text: str) -> dict:
    try:
        matches = re.findall(r"\{.*?\}", text, re.DOTALL)
        if not matches:
            raise ValueError("No se encontró un bloque JSON en el texto.")
        json_text = matches[0]
        return json.loads(json_text)
    except Exception as e:
        raise ValueError(f"Error al extraer JSON: {e}\nTexto recibido:\n{text}")

def normalizar_fechas_relativas(fecha_inicio, fecha_fin):
    hoy = datetime.today()
    
    def get_last_monday():
        # Calcula el lunes de la semana actual y luego resta 7 días para el lunes de la semana anterior.
        # weekday() devuelve 0 para lunes, 1 para martes, etc.
        days_since_monday = hoy.weekday()
        current_monday = hoy - timedelta(days=days_since_monday)
        return current_monday - timedelta(days=7) # El lunes de la semana pasada

    def to_str(date_obj):
        return date_obj.strftime("%Y-%m-%d")
    
    fecha_inicio_norm = fecha_inicio
    fecha_fin_norm = fecha_fin

    if fecha_inicio is not None and "lunes pasado" in fecha_inicio.lower():
        fecha_inicio_norm = to_str(get_last_monday())
    
    if fecha_fin is not None and "lunes pasado" in fecha_fin.lower():
        fecha_fin_norm = to_str(get_last_monday())

    return fecha_inicio_norm, fecha_fin_norm

## ---------------------------------------------------------
# 4. Nuevo Nodo: Filtro Inicial
# ---------------------------------------------------------

def filtrar_pregunta_inicial(state: ChatbotState) -> ChatbotState:
    pregunta = state["input"]
    prompt = PROMPT_FILTRO_INICIAL.format(pregunta=pregunta)
    
    # Aquí es donde pasarías el historial si el LLM necesitara contexto para la clasificación inicial.
    # Para la clasificación inicial de "saludo/fuera_de_alcance/válida", usualmente la pregunta actual es suficiente.
    # Obtenemos la respuesta bruta del LLM.
    respuesta_llm_raw = llm.invoke(prompt).content.strip().lower()

    # FIX: Eliminar cualquier formato de Markdown (como los asteriscos de negrita) de la respuesta del LLM.
    # Esto asegura que la comparación con 'categorias_validas' sea precisa.
    respuesta_llm_cleaned = respuesta_llm_raw.replace('**', '') 

    # Define categorías válidas para este filtro
    categorias_validas = {"saludo", "fuera_de_alcance", "valida"}
    
    # Usamos la respuesta limpia para detectar la categoría.
    categoria_detectada = respuesta_llm_cleaned if respuesta_llm_cleaned in categorias_validas else "fuera_de_alcance"
    
    print(f"[🚪 FILTRO INICIAL] Pregunta: {pregunta}")
    print(f"[🚪 FILTRO INICIAL] Prompt enviado:\n{prompt}")
    print(f"[🚪 FILTRO INICIAL] Respuesta del modelo (raw): {respuesta_llm_raw}") # Mostrar la raw para depuración
    print(f"[🚪 FILTRO INICIAL] Respuesta del modelo (cleaned): {respuesta_llm_cleaned}") # Mostrar la limpia para depuración
    print(f"[🚪 FILTRO INICIAL] Categoría detectada: {categoria_detectada}")

    response_message = None # Inicializa a None, para que no sobreescriba si es "valida"
    if categoria_detectada == "saludo":
        response_message = "¡Hola! ¿En qué puedo ayudarte hoy con información financiera o del mercado de valores?"
    elif categoria_detectada == "fuera_de_alcance":
        response_message = "Lo siento, soy un asistente especializado en finanzas y no puedo responder preguntas sobre ese tema. ¿Hay algo relacionado con el mercado de valores, cotizaciones o análisis financieros en lo que pueda ayudarte?"
    
    return {
        **state,
        "categoria_inicial": categoria_detectada,
        "respuesta": response_message # Solo se actualiza si hay un mensaje específico para estas categorías.
    }
# ---------------------------------------------------------
# 5. Nodo: Clasificación
# ---------------------------------------------------------

def clasificar_intencion(state: ChatbotState) -> ChatbotState:
    pregunta = state["input"]
    prompt = PROMPT_CLASIFICACION.format(pregunta=pregunta)
    
    # Para la clasificación de intención, usualmente la pregunta actual es suficiente,
    # el historial de chat completo podría ser excesivo o irrelevante para esta tarea específica.
    respuesta = llm.invoke(prompt).content.strip().lower()
    
    categorias_validas = {"series_temporales", "documentos_financieros", "consulta_api"}
    tipo = respuesta if respuesta in categorias_validas else "consulta_api" # Fallback por si la clasificación es errónea
    
    print(f"[🔍 CLASIFICADOR] Pregunta: {state['input']}")
    print(f"[🔍 CLASIFICADOR] Prompt enviado:\n{prompt}")
    print(f"[🔍 CLASIFICADOR] Respuesta del modelo: {respuesta}")
    print(f"[🔍 CLASIFICADOR] Tipo detectado: {tipo}")

    return {**state, "tipo_pregunta": tipo, "fuente": "clasificador"}

# ---------------------------------------------------------
# 6. Nodo de decisión principal (después del filtro inicial)
# ---------------------------------------------------------

def seleccionar_ruta_inicial(state: ChatbotState) -> str:
    # Este es el nuevo selector principal después del filtro inicial
    if state["categoria_inicial"] in ["saludo", "fuera_de_alcance"]:
        return "finalizar_temprano"
    return "clasificar" # Si es "valida", se dirige al nodo de clasificación

# ---------------------------------------------------------
# 7. Nodo de decisión secundario (después del clasificador)
# ---------------------------------------------------------

def seleccionar_fuente(state: ChatbotState) -> str:
    # Este es el selector existente para las preguntas válidas
    return state["tipo_pregunta"]

# ---------------------------------------------------------
# 8. Nodo: Series temporales
# ---------------------------------------------------------

def analizar_series_temporales(state: ChatbotState) -> ChatbotState:
    pregunta = state["input"]
    prompt = PROMPT_SERIES.format(pregunta=pregunta)
    
    # Pasar el historial de chat para que el LLM tenga contexto si lo necesita para la respuesta simulada
    # En este caso, PROMPT_SERIES ya tiene un placeholder para {pregunta}, así que se usa directamente.
    # Si quisieras que el LLM tuviera en cuenta el historial para generar la "respuesta simulada",
    # tendrías que reestructurar la invocación del LLM para pasar una lista de mensajes.
    # Por ahora, se mantiene como estaba, asumiendo que el prompt es auto-contenido.
    response = llm.invoke(prompt)
    data = extract_json(response.content)

    empresa = data.get("empresa", "BBVA").upper()
    # Asegúrate de que lag sea un entero, con un valor por defecto sensato.
    try:
        lag = int(data.get("lag", 1))
    except ValueError:
        lag = 1 # Valor por defecto si no es un número válido

    respuesta_simulada = data.get("respuesta", "")

    modelos_dir = "./modelos_por_empresa"
    path_csv = "IBEX35_cotizaciones_20_Limpio.csv"

    resultado = ejecutar_prediccion(empresa, lag, path_csv, modelos_dir)

    respuesta_modelo = resultado.get("respuesta", "No se pudo obtener la predicción real.")
    grafico_base64 = resultado.get("grafico_base64")

    return {
        **state,
        "respuesta": f"{respuesta_simulada}\n\n📈 Predicción real:\n{respuesta_modelo}",
        "fuente": "series_temporales",
        "empresa": empresa,
        "grafico_base64": grafico_base64
    }


# ---------------------------------------------------------
# 9. Nodo: Documentos financieros -> Qdrant
# ---------------------------------------------------------

def consulta_qdrant(state: ChatbotState) -> ChatbotState:
    pregunta = state["input"]
    
    resultados = buscar_en_qdrant(pregunta)
    fragmentos = [r.payload.get("fragmento", "") for r in resultados]
    contexto = "\n\n".join(fragmentos)

    prompt_rag = PROMPT_RAG_DOCUMENTOS.format(contexto=contexto, pregunta=pregunta)
    
    # Para RAG, es útil pasar el historial de chat para que el LLM pueda contextualizar
    # la respuesta basada en fragmentos y la conversación previa.
    # Aquí reestructuramos la llamada a `llm.invoke` para usar la lista de mensajes.
    messages_for_llm = state["chat_history"] + [HumanMessage(content=prompt_rag)]
    respuesta_llm = llm.invoke(messages_for_llm).content.strip()

    try:
        data = extract_json(respuesta_llm)
        respuesta_final = data.get("respuesta", "(El modelo no devolvió una clave 'respuesta').")
    except Exception as e:
        print(f"⚠️ Error extrayendo JSON del LLM: {e}")
        respuesta_final = respuesta_llm

    respuesta_final = respuesta_final.replace(". ", ". \n").replace("- ", "• ")

    return {
        **state,
        "respuesta": respuesta_final,
        "fuente": "qdrant",
        "fragmentos": fragmentos
    }

# ---------------------------------------------------------
# 10. Nodo: Consulta API financiera
# ---------------------------------------------------------

def consultar_api_financiera(state: ChatbotState) -> ChatbotState:
    pregunta = state["input"]
    print(f"[🌐 Nodo API] Pregunta: {pregunta}")
    
    # Para la extracción de parámetros, a menudo solo se necesita la pregunta actual.
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
            "respuesta": "❌ Faltan parámetros clave: empresa, fecha de inicio o fin. Por favor, especifica estos datos.",
            "fuente": "api"
        }

    # Para la simulación de respuesta del LLM, pasar el historial es clave para un mejor contexto.
    simulacion_prompt_text = PROMPT_API.format(pregunta=pregunta)
    messages_for_simulacion = state["chat_history"] + [HumanMessage(content=simulacion_prompt_text)]
    simulacion_response = llm.invoke(messages_for_simulacion)
    
    print(f"[🌐 Nodo API] Prompt de simulación:\n{simulacion_prompt_text}")
    print(f"[🌐 Nodo API] Respuesta simulada:\n{simulacion_response.content}")

    try:
        data_simulada = extract_json(simulacion_response.content)
        respuesta_simulada = data_simulada.get("respuesta", "(El LLM no devolvió una clave 'respuesta')")
    except Exception as e:
        print(f"⚠️ Error extrayendo respuesta simulada: {e}")
        respuesta_simulada = "(No se pudo generar una respuesta simulada del LLM)"

    resultado = construir_respuesta_yfinance(empresa, fecha_inicio, fecha_fin)
    print(f"[🌐 Nodo API] Respuesta real:\n{resultado['respuesta']}")

    # Combina la respuesta simulada del LLM con los datos reales
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
# 11. Construcción del grafo
# ---------------------------------------------------------

def build_graph():
    graph = StateGraph(ChatbotState)
    # Añadir el nuevo nodo de filtro inicial
    graph.add_node("filtro_inicial", RunnableLambda(filtrar_pregunta_inicial))
    graph.add_node("clasificar", RunnableLambda(clasificar_intencion))
    graph.add_node("series_temporales", RunnableLambda(analizar_series_temporales))
    graph.add_node("consulta_qdrant", RunnableLambda(consulta_qdrant))
    graph.add_node("consulta_api", RunnableLambda(consultar_api_financiera))

    # El punto de entrada ahora es el filtro inicial
    graph.set_entry_point("filtro_inicial")

    # Nueva lógica de decisión después del filtro inicial
    graph.add_conditional_edges(
        "filtro_inicial",
        seleccionar_ruta_inicial, # Función que decide el próximo nodo
        {
            "clasificar": "clasificar",       # Si es "valida", va al clasificador
            "finalizar_temprano": END         # Si es saludo o fuera de alcance, termina aquí
        }
    )

    # Las transiciones existentes desde el clasificador se mantienen
    graph.add_conditional_edges("clasificar", seleccionar_fuente, {
        "series_temporales": "series_temporales",
        "documentos_financieros": "consulta_qdrant",
        "consulta_api": "consulta_api"
    })

    # Las aristas a END desde los nodos finales se mantienen
    graph.add_edge("series_temporales", END)
    graph.add_edge("consulta_qdrant", END)
    graph.add_edge("consulta_api", END)

    return graph.compile()

# Compilamos el grafo
graph = build_graph()

# --- Función para probar el chatbot con memoria ---
def run_chatbot_with_memory():
    chat_history: list[BaseMessage] = [] # Inicializa el historial de chat

    print("¡Hola! Soy tu asistente financiero. Escribe 'salir' para terminar la conversación.")
    while True:
        user_input = input("Tú: ")
        if user_input.lower() == "salir":
            print("¡Adiós! Que tengas un buen día.")
            break

        # Prepara el estado inicial incluyendo el historial actual
        initial_state = {
            "input": user_input,
            "chat_history": chat_history, # Pasa el historial al estado
            "empresa": None,
            "tipo_pregunta": None,
            "respuesta": None,
            "fuente": None,
            "fecha_inicio": None,
            "fecha_fin": None,
            "grafico_base64": None,
            "categoria_inicial": None
        }

        # Ejecuta el grafo
        # LangGraph automáticamente pasa el estado de un nodo a otro
        final_state = graph.invoke(initial_state)

        # Obtén la respuesta del chatbot
        # El filtro inicial puede haber puesto una respuesta si la pregunta era "saludo" o "fuera_de_alcance"
        bot_response = final_state.get("respuesta", "Lo siento, no pude procesar tu solicitud.")
        print(f"Bot: {bot_response}")

        # Actualiza el historial de chat para la próxima interacción
        chat_history.append(HumanMessage(content=user_input))
        chat_history.append(AIMessage(content=bot_response))

        # Opcional: Limita el tamaño del historial para evitar que sea demasiado largo
        # Por ejemplo, mantener solo las últimas 5 interacciones completas (10 mensajes)
        if len(chat_history) > 10:
            chat_history = chat_history[-10:]

# Para ejecutar el chatbot desde este script:
# if __name__ == "__main__":
#     run_chatbot_with_memory()