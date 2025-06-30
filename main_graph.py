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
# Asegúrate de que PROMPT_CLASIFICACION en prompts.py devuelva JSON
from prompts import PROMPT_SERIES, PROMPT_API_EXTRAER, PROMPT_CLASIFICACION, PROMPT_RAG_DOCUMENTOS
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
    input: str # Pregunta original del usuario
    empresa: Optional[str]
    tipo_pregunta: Optional[str]
    respuesta: Optional[str]
    fuente: Optional[str]
    fecha_inicio: Optional[str]
    fecha_fin: Optional[str]
    grafico_base64: Optional[str]
    historial_preguntas: Optional[list[str]] # Para las últimas 3 preguntas del usuario (originales)
    historial_completo: Optional[list[dict]] # Para guardar preguntas y respuestas completas
    pregunta_completa: Optional[str] # Nueva variable para la pregunta re-escrita y desambiguada
    fecha_actual: Optional[str] # Campo para la fecha actual

# ---------------------------------------------------------
# 3. Funciones auxiliares
# ---------------------------------------------------------

def extract_json(text: str) -> dict:
    try:
        # Buscar el bloque de JSON en el texto
        # Se modificó para buscar específicamente un bloque de código JSON si está presente,
        # o solo un objeto JSON si no hay bloque de código.
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
        if json_match:
            json_text = json_match.group(1)
        else:
            # Fallback a buscar cualquier {} si no se encuentra el bloque de código
            matches = re.findall(r"\{.*?\}", text, re.DOTALL)
            if not matches:
                raise ValueError("No se encontró un bloque JSON en el texto.")
            json_text = matches[0]

        # Intentamos cargar el JSON
        return json.loads(json_text)
    except Exception as e:
        raise ValueError(f"Error al extraer JSON: {e}\nTexto recibido:\n{text}")

def normalizar_fechas_relativas(fecha_inicio, fecha_fin):
    hoy_dt = datetime.today()

    def get_last_monday(date_ref):
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
        # Puedes añadir más lógicas de fecha relativa aquí

    # Handle fecha_fin
    if fecha_fin:
        fecha_fin_lower = fecha_fin.lower()
        if "lunes pasado" in fecha_fin_lower:
            fecha_fin = to_str(get_last_monday(hoy_dt))
        elif "hoy" in fecha_fin_lower:
            fecha_fin = to_str(hoy_dt)
        # Puedes añadir más lógicas de fecha relativa aquí

    # Si las fechas siguen sin normalizarse a YYYY-MM-DD, intentar parsearlas
    if fecha_inicio and not re.match(r"\d{4}-\d{2}-\d{2}", fecha_inicio):
        try:
            parsed_date = datetime.strptime(fecha_inicio, "%Y-%m-%d")
            fecha_inicio = to_str(parsed_date)
        except ValueError:
            print(f"Advertencia: No se pudo normalizar fecha_inicio: {fecha_inicio}")
            fecha_inicio = None

    if fecha_fin and not re.match(r"\d{4}-\d{2}-\d{2}", fecha_fin):
        try:
            parsed_date = datetime.strptime(fecha_fin, "%Y-%m-%d")
            fecha_fin = to_str(parsed_date)
        except ValueError:
            print(f"Advertencia: No se pudo normalizar fecha_fin: {fecha_fin}")
            fecha_fin = None

    return fecha_inicio, fecha_fin # Corregido: Retorna solo fecha_inicio y fecha_fin

# ---------------------------------------------------------
# 4. Nodo: Clasificación (Actualizado para historial y pregunta_completa)
# ---------------------------------------------------------

def clasificar_intencion(state: ChatbotState) -> ChatbotState:
    pregunta_original = state["input"]
    historial_preguntas_previas = state.get("historial_preguntas", [])
    historial_para_prompt = "\n".join(historial_preguntas_previas) if historial_preguntas_previas else "No hay historial previo."
    fecha_actual = state.get("fecha_actual", datetime.now().strftime("%Y-%m-%d"))

    # Formatear el prompt con la pregunta del usuario, el historial, y la fecha actual
    prompt = PROMPT_CLASIFICACION.format(
        pregunta_original=pregunta_original,
        historial_conversacion=historial_para_prompt,
        fecha_actual=fecha_actual
    )

    respuesta_llm = llm.invoke(prompt).content.strip()

    # Extraer JSON con clasificación, pregunta_completa y justificacion
    tipo = "consulta_api" # Valor por defecto si falla la extracción o clasificación
    pregunta_completa = pregunta_original # Valor por defecto
    justificacion = "No se pudo obtener una justificación." # Valor por defecto para justificación

    try:
        data = extract_json(respuesta_llm)
        tipo = data.get("clasificacion", "consulta_api").lower()
        pregunta_completa = data.get("pregunta_completa", pregunta_original)
        justificacion = data.get("justificacion", "No se encontró justificación en la respuesta del LLM.")
        
        # Validar tipo de pregunta
        categorias_validas = {"series_temporales", "documentos_financieros", "consulta_api"}
        if tipo not in categorias_validas:
            print(f"⚠️ Tipo de pregunta '{tipo}' no válido. Usando 'consulta_api' como fallback.")
            tipo = "consulta_api"

    except ValueError as e:
        print(f"❌ Error al extraer JSON de clasificación/pregunta_completa/justificacion: {e}\nRespuesta RAW del LLM:\n{respuesta_llm}")
        justificacion = f"Error al parsear la respuesta del LLM: {e}"


    print(f"\n--- [🔍 CLASIFICADOR] DEBUGGING INFO ---") # Separador para claridad
    print(f"[🔍 CLASIFICADOR] Prompt enviado al LLM:\n{prompt}") # Nuevo: Imprimir el prompt completo
    print(f"[🔍 CLASIFICADOR] Respuesta RAW del LLM:\n{respuesta_llm}")
    print(f"[🔍 CLASIFICADOR] Pregunta original: {pregunta_original}")
    print(f"[🔍 CLASIFICADOR] Pregunta completa generada: {pregunta_completa}")
    print(f"[🔍 CLASIFICADOR] Tipo detectado: {tipo}")
    print(f"[🔍 CLASIFICADOR] Justificación: {justificacion}")
    print(f"--- [🔍 CLASIFICADOR] FIN DEBUGGING INFO ---\n")

    # Actualizar historial_preguntas (solo las últimas 3 preguntas del usuario)
    historial_preguntas_actualizado = historial_preguntas_previas + [pregunta_original]
    historial_preguntas_actualizado = historial_preguntas_actualizado[-3:]

    return {
        **state,
        "tipo_pregunta": tipo,
        "pregunta_completa": pregunta_completa,
        "historial_preguntas": historial_preguntas_actualizado,
        "fuente": "clasificador"
    }

# ---------------------------------------------------------
# 5. Nodo de decisión
# ---------------------------------------------------------

def seleccionar_fuente(state: ChatbotState) -> str:
    return state["tipo_pregunta"]

# ---------------------------------------------------------
# 6. Nodo: Series temporales (Ahora usa pregunta_original y pregunta_completa)
# ---------------------------------------------------------

def analizar_series_temporales(state: ChatbotState) -> ChatbotState:
    pregunta_original = state["input"]
    pregunta_completa = state["pregunta_completa"]
    fecha_actual = state.get("fecha_actual", datetime.now().strftime("%Y-%m-%d")) # Obtener fecha actual del estado
    print(f"[📊 SERIES] Analizando series temporales con:\n   Original: '{pregunta_original}'\n   Completa: '{pregunta_completa}'\n   Fecha Actual: '{fecha_actual}'")

    prompt = PROMPT_SERIES.format(
        pregunta_original=pregunta_original,
        pregunta_completa=pregunta_completa,
        fecha_actual=fecha_actual # Pasar fecha_actual al prompt
    )
    response = llm.invoke(prompt)
    try:
        data = extract_json(response.content)
    except Exception as e:
        print(f"⚠️ Error extrayendo JSON del LLM en nodo Series Temporales: {e}")
        return {
            **state,
            "respuesta": "❌ No se pudo extraer la información necesaria para la predicción de series temporales.",
            "fuente": "series_temporales"
        }

    empresa = data.get("empresa", "BBVA").upper()
    lag = int(data.get("lag", 1))
    # En este punto, 'respuesta_simulada' es generada por el LLM como un ejemplo
    respuesta_simulada = data.get("respuesta", "")

    print(f"[📊 SERIES] Empresa detectada: {empresa}, lag: {lag}")
    print(f"[📊 SERIES] Respuesta simulada (del LLM): {respuesta_simulada}")

    modelos_dir = os.path.join(os.getcwd(), "modelos_por_empresa")
    path_csv = os.path.join(os.getcwd(), "IBEX35_cotizaciones_20_Limpio.csv")

    resultado = ejecutar_prediccion(empresa, lag, path_csv, modelos_dir)
    respuesta_real_modelo = resultado.get("respuesta", "No se pudo obtener la predicción real.")
    
    # Priorizamos la respuesta real si está disponible y es relevante
    final_respuesta = respuesta_real_modelo if "No se pudo obtener" not in respuesta_real_modelo else respuesta_simulada

    return {
        **state,
        "respuesta": final_respuesta,
        "fuente": "series_temporales",
        "empresa": empresa
    }

# ---------------------------------------------------------
# 7. Nodo: Documentos financieros -> Qdrant (Ahora usa pregunta_original y pregunta_completa)
# ---------------------------------------------------------

def consulta_qdrant(state: ChatbotState) -> ChatbotState:
    pregunta_original = state["input"]
    pregunta_completa = state["pregunta_completa"] # La usamos para la búsqueda y para el prompt
    fecha_actual = state.get("fecha_actual", datetime.now().strftime("%Y-%m-%d")) # Obtener fecha actual del estado
    print(f"\n[📚 Nodo RAG] ✅ Entrada al nodo 'consulta_qdrant' con:\n   Original: '{pregunta_original}'\n   Completa: '{pregunta_completa}'\n   Fecha Actual: '{fecha_actual}'")

    try:
        print("[📚 Nodo RAG] Buscando fragmentos en Qdrant...")
        resultados = buscar_en_qdrant(pregunta_completa) # La búsqueda sigue usando la pregunta_completa por su claridad

        fragmentos = [r.payload.get("fragmento", "") for r in resultados if r.payload and r.payload.get("fragmento")]
        
        if not fragmentos:
            print("[📚 Nodo RAG] ⚠️ No se encontraron fragmentos relevantes en Qdrant.")
            return {
                **state,
                "respuesta": "Lo siento, no pude encontrar información relevante en mis documentos financieros para responder a tu pregunta. ¿Podrías reformularla o buscar algo diferente?",
                "fuente": "qdrant",
                "fragmentos": []
            }

        contexto = "\n\n".join(fragmentos)
        print(f"[📚 Nodo RAG] Contexto enviado al LLM (primeros 500 chars):\n'{contexto[:500]}...'")

        # Pasar ambas preguntas y fecha_actual al prompt RAG
        prompt_rag = PROMPT_RAG_DOCUMENTOS.format(
            contexto=contexto,
            pregunta_original=pregunta_original,
            pregunta_completa=pregunta_completa,
            fecha_actual=fecha_actual # Pasar fecha_actual al prompt
        )
        print(f"[📚 Nodo RAG] Prompt RAG enviado al LLM (primeros 500 chars):\n'{prompt_rag[:500]}...'")

        print("[📚 Nodo RAG] Invocando LLM para generar respuesta RAG...")
        llm_response_object = llm.invoke(prompt_rag)
        llm_response_raw = llm_response_object.content.strip()
        print(f"[📚 Nodo RAG] Respuesta RAW del LLM:\n'{llm_response_raw}'")

        respuesta_final_text = llm_response_raw
        respuesta_final_text = respuesta_final_text.replace(". ", ". \n").replace("- ", "• ")

        print(f"[📚 Nodo RAG] ✅ Respuesta final generada (primeros 500 chars):\n'{respuesta_final_text[:500]}...'")

        return {
            **state,
            "respuesta": respuesta_final_text,
            "fuente": "qdrant",
            "fragmentos": fragmentos
        }

    except Exception as general_e:
        print(f"❌ Error CRÍTICO y general en el nodo Qdrant: {general_e}")
        return {
            **state,
            "respuesta": f"Lo siento mucho, hubo un problema técnico inesperado al procesar tu solicitud de documentos financieros. Detalles: {general_e}. Por favor, inténtalo de nuevo o formula la pregunta de otra manera.",
            "fuente": "error_qdrant",
            "fragmentos": []
        }

# ---------------------------------------------------------
# 8. Nodo: Consulta API financiera (Ahora usa pregunta_original y pregunta_completa)
# ---------------------------------------------------------

def consultar_api_financiera(state: ChatbotState) -> ChatbotState:
    pregunta_original = state["input"]
    pregunta_para_api_extraccion = state["pregunta_completa"]
    fecha_actual = state["fecha_actual"] # Usar la fecha actual del estado
    print(f"[🌐 Nodo API] Pregunta original para extracción: {pregunta_original}")
    print(f"[🌐 Nodo API] Pregunta completa para extracción: {pregunta_para_api_extraccion}")
    print(f"[🌐 Nodo API] Fecha actual (del estado): {fecha_actual}")


    extraction_prompt = PROMPT_API_EXTRAER.format(
        pregunta_original=pregunta_original,
        pregunta_completa=pregunta_para_api_extraccion,
        fecha_actual=fecha_actual # Pasar fecha_actual del estado
    )
    
    print(f"[🌐 Nodo API] Prompt de extracción:\n{extraction_prompt}")
    
    response = llm.invoke(extraction_prompt)
    llm_response_content = response.content.strip()
    
    print(f"[🌐 Nodo API] Respuesta LLM para extracción CRUDA:\n'{llm_response_content}'")
    
    try:
        data = extract_json(llm_response_content)
        print(f"[🌐 Nodo API] Datos extraídos del LLM:\n{data}")

        empresa = data.get("empresa")
        if not empresa:
            print("⚠️ No se pudo extraer la empresa del JSON")
        empresa_normalizada = empresa.strip().lower() if empresa else None  
        print(f"[🌐 Nodo API] Empresa normalizada: {empresa_normalizada}")
        
        fecha_inicio = data.get("fecha_inicio")
        fecha_fin = data.get("fecha_fin")
        fecha_inicio, fecha_fin = normalizar_fechas_relativas(fecha_inicio, fecha_fin)
        print(f"[🌐 Nodo API] Fechas normalizadas: {fecha_inicio}, {fecha_fin}")

    except Exception as e:
        print(f"⚠️ Error extrayendo parámetros para API: {e}")
        return {
            **state,
            "respuesta": "❌ No se pudieron extraer los parámetros necesarios para consultar los datos.",
            "fuente": "api"
        }

    if not all([empresa_normalizada, fecha_inicio, fecha_fin]):
        print(f"⚠️ Faltan parámetros clave: empresa={empresa_normalizada}, fecha_inicio={fecha_inicio}, fecha_fin={fecha_fin}")
        return {
            **state,
            "respuesta": "❌ Faltan parámetros clave: empresa, fecha de inicio o fin. Por favor, sé más específico.",
            "fuente": "api"
        }

    resultado = construir_respuesta_yfinance(empresa_normalizada, fecha_inicio, fecha_fin)
    print(f"[🌐 Nodo API] Resultado de la API financiera:\n{resultado['respuesta']}")

    return {
        **state,
        "respuesta": resultado['respuesta'],
        "fuente": "api",
        "empresa": empresa_normalizada,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin
    }

# ---------------------------------------------------------
# 9. Nodo: Actualizar Historial Completo
# ---------------------------------------------------------

def actualizar_historial_final(state: ChatbotState) -> ChatbotState:
    historial_completo_previo = state.get("historial_completo", [])
    
    # Añadir la última interacción al historial completo
    nueva_entrada = {
        "pregunta_usuario": state["input"],
        "pregunta_procesada": state.get("pregunta_completa", state["input"]),
        "respuesta_asistente": state.get("respuesta", "No se pudo generar una respuesta."),
        "fuente": state.get("fuente", "desconocida"),
        "timestamp": datetime.now().isoformat()
    }
    
    historial_completo_actualizado = historial_completo_previo + [nueva_entrada]

    # Limitar el historial completo a las últimas 10 interacciones (puedes ajustar este número)
    historial_completo_actualizado = historial_completo_actualizado[-10:] 

    print(f"[🔄 HISTORIAL] Historial completo actualizado. Total entradas: {len(historial_completo_actualizado)}")
    print(f"[🔄 HISTORIAL] Última entrada: {nueva_entrada}")

    return {
        **state,
        "historial_completo": historial_completo_actualizado
    }


# ---------------------------------------------------------
# 10. Construcción del grafo (Actualizado con nuevo nodo de historial)
# ---------------------------------------------------------

def build_graph():
    graph = StateGraph(ChatbotState)
    graph.add_node("clasificar", RunnableLambda(clasificar_intencion))
    graph.add_node("series_temporales", RunnableLambda(analizar_series_temporales))
    graph.add_node("consulta_qdrant", RunnableLambda(consulta_qdrant))
    graph.add_node("consulta_api", RunnableLambda(consultar_api_financiera))
    graph.add_node("actualizar_historial", RunnableLambda(actualizar_historial_final)) # Nuevo nodo

    graph.set_entry_point("clasificar")

    graph.add_conditional_edges("clasificar", seleccionar_fuente, {
        "series_temporales": "series_temporales",
        "documentos_financieros": "consulta_qdrant",
        "consulta_api": "consulta_api"
    })

    # Ahora los nodos específicos pasan por 'actualizar_historial' antes de terminar
    graph.add_edge("series_temporales", "actualizar_historial")
    graph.add_edge("consulta_qdrant", "actualizar_historial")
    graph.add_edge("consulta_api", "actualizar_historial")
    
    # Y el nodo de historial es el que lleva al final
    graph.add_edge("actualizar_historial", END)

    return graph.compile()

# Compilamos el grafo
graph = build_graph()


if __name__ == "__main__":
    # --- Simulación de una conversación ---
    
    # Primer turno: Pregunta sobre una empresa específica
    print("\n--- Turno 1: Precio de Repsol ---")
    initial_state_1 = {
        "input": "¿Cuál es el precio actual de Repsol?",
        "historial_preguntas": [], # Nuevo
        "historial_completo": [],    # Nuevo
        "fecha_actual": datetime.now().strftime("%Y-%m-%d") # Pasar la fecha actual al estado inicial
    }
    final_state_1 = graph.invoke(initial_state_1)
    print(f"\nRespuesta del bot: {final_state_1.get('respuesta')}")
    print(f"Tipo de pregunta: {final_state_1.get('tipo_pregunta')}")
    print(f"Pregunta completa: {final_state_1.get('pregunta_completa')}")
    print(f"Historial de preguntas (para el siguiente turno): {final_state_1.get('historial_preguntas')}")
    print(f"Historial completo (al final del turno): {final_state_1.get('historial_completo')}")

    # Segundo turno: Pregunta de seguimiento (se espera que use el contexto)
    print("\n--- Turno 2: Y mañana? ---")
    initial_state_2 = {
        "input": "¿Y mañana?",
        "historial_preguntas": final_state_1["historial_preguntas"], # Pasar historial del turno anterior
        "historial_completo": final_state_1["historial_completo"],      # Pasar historial completo
        "fecha_actual": datetime.now().strftime("%Y-%m-%d") # Pasar la fecha actual al estado inicial
    }
    final_state_2 = graph.invoke(initial_state_2)
    print(f"\nRespuesta del bot: {final_state_2.get('respuesta')}")
    print(f"Tipo de pregunta: {final_state_2.get('tipo_pregunta')}")
    print(f"Pregunta completa: {final_state_2.get('pregunta_completa')}")
    print(f"Historial de preguntas (para el siguiente turno): {final_state_2.get('historial_preguntas')}")
    print(f"Historial completo (al final del turno): {final_state_2.get('historial_completo')}")

    # Tercer turno: Pregunta sobre informes (cambio de contexto)
    print("\n--- Turno 3: Beneficios de BBVA ---")
    initial_state_3 = {
        "input": "¿Qué beneficios obtuvo BBVA en 2023?",
        "historial_preguntas": final_state_2["historial_preguntas"],
        "historial_completo": final_state_2["historial_completo"],
        "fecha_actual": datetime.now().strftime("%Y-%m-%d") # Pasar la fecha actual al estado inicial
    }
    final_state_3 = graph.invoke(initial_state_3)
    print(f"\nRespuesta del bot: {final_state_3.get('respuesta')}")
    print(f"Tipo de pregunta: {final_state_3.get('tipo_pregunta')}")
    print(f"Pregunta completa: {final_state_3.get('pregunta_completa')}")
    print(f"Historial de preguntas (para el siguiente turno): {final_state_3.get('historial_preguntas')}")
    print(f"Historial completo (al final del turno): {final_state_3.get('historial_completo')}")

    # Cuarto turno: Otro seguimiento (debería seguir el último contexto de BBVA)
    print("\n--- Turno 4: Y su estrategia de sostenibilidad? ---")
    initial_state_4 = {
        "input": "¿Y su estrategia de sostenibilidad?",
        "historial_preguntas": final_state_3["historial_preguntas"],
        "historial_completo": final_state_3["historial_completo"],
        "fecha_actual": datetime.now().strftime("%Y-%m-%d") # Pasar la fecha actual al estado inicial
    }
    final_state_4 = graph.invoke(initial_state_4)
    print(f"\nRespuesta del bot: {final_state_4.get('respuesta')}")
    print(f"Tipo de pregunta: {final_state_4.get('tipo_pregunta')}")
    print(f"Pregunta completa: {final_state_4.get('pregunta_completa')}")
    print(f"Historial de preguntas (para el siguiente turno): {final_state_4.get('historial_preguntas')}")
    print(f"Historial completo (al final del turno): {final_state_4.get('historial_completo')}")

    # Quinto turno: Nueva pregunta, el historial de 3 preguntas debería ser (BBVA sostenibilidad, beneficios BBVA, y mañana?)
    print("\n--- Turno 5: Precio de Santander la semana pasada ---")
    initial_state_5 = {
        "input": "¿Cuál fue el precio promedio de Santander la semana pasada?",
        "historial_preguntas": final_state_4["historial_preguntas"],
        "historial_completo": final_state_4["historial_completo"],
        "fecha_actual": datetime.now().strftime("%Y-%m-%d") # Pasar la fecha actual al estado inicial
    }
    final_state_5 = graph.invoke(initial_state_5)
    print(f"\nRespuesta del bot: {final_state_5.get('respuesta')}")
    print(f"Tipo de pregunta: {final_state_5.get('tipo_pregunta')}")
    print(f"Pregunta completa: {final_state_5.get('pregunta_completa')}")
    print(f"Historial de preguntas (para el siguiente turno): {final_state_5.get('historial_preguntas')}")
    print(f"Historial completo (al final del turno): {final_state_5.get('historial_completo')}")
