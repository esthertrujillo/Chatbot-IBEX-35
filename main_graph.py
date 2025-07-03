import os
import re
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from typing import Optional, List, Dict, Any
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableLambda
from langchain_groq import ChatGroq

from qdrant_utils import buscar_en_qdrant 
from prompts import PROMPT_SERIES, PROMPT_API_EXTRAER, PROMPT_CLASIFICACION, PROMPT_RAG_DOCUMENTOS
from cotizaciones import construir_respuesta_yfinance # Esta función debería devolver una respuesta estructurada o el precio
from series_model import ejecutar_prediccion 

# ---------------------------------------------------------
# 1. Configuración del modelo
# ---------------------------------------------------------

load_dotenv()
print("GROQ_API_KEY cargada:", os.getenv("GROQ_API_KEY"))

llm = ChatGroq(
    groq_api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama3-8b-8192", 
    temperature=0.1
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
    historial_preguntas: Optional[List[str]] 
    historial_completo: Optional[List[Dict[str, Any]]] 
    pregunta_completa: Optional[str] 
    fecha_actual: Optional[str] 
    datos_recopilados: Optional[Dict[str, Any]] # Para almacenar datos para la comparación
    # NUEVO: Campo para guardar datos estructurados por empresa
    datos_empresa_cache: Optional[Dict[str, Dict[str, Any]]] 


# ---------------------------------------------------------
# 3. Funciones auxiliares
# ---------------------------------------------------------


def extract_json(text):
    """
    Attempts to extract a JSON object from a given text string.
    It first looks for a JSON block enclosed in ```json...```.
    If not found, it tries to find a standalone JSON object {}.
    """
    print(f"[DEBUG - extract_json] Attempting to extract JSON from text:\n{text[:500]}...") # Print first 500 chars

    # 1. Try to find a JSON block enclosed in ```json and ```
    # re.DOTALL allows '.' to match newlines
    match_code_block = re.search(r'```json\s*(\{.*\})\s*```', text, re.DOTALL)
    if match_code_block:
        try:
            json_str = match_code_block.group(1)
            print(f"[DEBUG - extract_json] Found JSON in code block. Attempting to decode: {json_str[:200]}...")
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"[ERROR - extract_json] Decoding JSON from code block failed: {e}")
            print(f"[ERROR - extract_json] Problematic text: {json_str}")
            # Fall through to try standalone match if code block failed to decode

    match_standalone = re.search(r'(\{.*?\})', text, re.DOTALL) 
    if match_standalone:
        try:
            json_str = match_standalone.group(1)
            print(f"[DEBUG - extract_json] Found standalone JSON. Attempting to decode: {json_str[:200]}...")
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"[ERROR - extract_json] Decoding standalone JSON failed: {e}")
            print(f"[ERROR - extract_json] Problematic text: {json_str}")
            return None # If standalone fails, there's likely no valid JSON
    
    print("[ERROR - extract_json] No valid JSON block found in the text.")
    return None # No JSON block found at all


def normalizar_fechas_relativas(fecha_inicio: Optional[str], fecha_fin: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    hoy_dt = datetime.today()

    def get_last_monday(date_ref):
        return date_ref - timedelta(days=date_ref.weekday() + 7) 

    def to_str(date_obj):
        return date_obj.strftime("%Y-%m-%d")

    if fecha_inicio:
        fecha_inicio_lower = fecha_inicio.lower()
        if "lunes pasado" in fecha_inicio_lower:
            fecha_inicio = to_str(get_last_monday(hoy_dt))
        elif "hoy" in fecha_inicio_lower:
            fecha_inicio = to_str(hoy_dt)
        elif "ayer" in fecha_inicio_lower:
            fecha_inicio = to_str(hoy_dt - timedelta(days=1))
    
    if fecha_fin:
        fecha_fin_lower = fecha_fin.lower()
        if "lunes pasado" in fecha_fin_lower: 
            fecha_fin = to_str(get_last_monday(hoy_dt) + timedelta(days=4)) 
        elif "hoy" in fecha_fin_lower:
            fecha_fin = to_str(hoy_dt)
        elif "ayer" in fecha_fin_lower:
            fecha_fin = to_str(hoy_dt - timedelta(days=1))

    if fecha_inicio and not re.match(r"\d{4}-\d{2}-\d{2}", fecha_inicio):
        try:
            parsed_date = datetime.strptime(fecha_inicio + f"-{hoy_dt.year}", "%m-%d-%Y")
            fecha_inicio = to_str(parsed_date)
        except ValueError:
            try: 
                parsed_date = datetime.strptime(fecha_inicio, "%Y-%m-%d")
                fecha_inicio = to_str(parsed_date)
            except ValueError:
                pass 

    if fecha_fin and not re.match(r"\d{4}-\d{2}-\d{2}", fecha_fin):
        try:
            parsed_date = datetime.strptime(fecha_fin + f"-{hoy_dt.year}", "%m-%d-%Y")
            fecha_fin = to_str(parsed_date)
        except ValueError:
            try:
                parsed_date = datetime.strptime(fecha_fin, "%Y-%m-%d")
                fecha_fin = to_str(parsed_date)
            except ValueError:
                pass 

    return fecha_inicio, fecha_fin


# ---------------------------------------------------------
# 4. Nodo: Clasificación
# ---------------------------------------------------------

def clasificar_intencion(state: ChatbotState) -> ChatbotState:
    pregunta_original = state["input"]
    historial_preguntas_previas = state.get("historial_preguntas", [])
    historial_para_prompt = "\n".join(historial_preguntas_previas) if historial_preguntas_previas else "No hay historial previo."
    fecha_actual = state.get("fecha_actual", datetime.now().strftime("%Y-%m-%d"))

    prompt = PROMPT_CLASIFICACION.format(
        pregunta_original=pregunta_original,
        historial_conversacion=historial_para_prompt,
        fecha_actual=fecha_actual # Pasamos la fecha actual
    )

    respuesta_llm = llm.invoke(prompt).content.strip()

    tipo = "consulta_api" 
    pregunta_completa = pregunta_original 
    justificacion = "No se pudo obtener una justificación." 

    try:
        data = extract_json(respuesta_llm)
        tipo = data.get("clasificacion", "consulta_api").lower()
        pregunta_completa = data.get("pregunta_completa", pregunta_original)
        justificacion = data.get("justificacion", "No se encontró justificación en la respuesta del LLM.")
        
        # Eliminada 'comparacion_financiera' de categorías válidas
        categorias_validas = {"series_temporales", "documentos_financieros", "consulta_api"}
        if tipo not in categorias_validas:
            print(f"⚠️ Tipo de pregunta '{tipo}' no válido. Usando 'consulta_api' como fallback.")
            tipo = "consulta_api"

    except ValueError as e:
        print(f"❌ Error al extraer JSON de clasificación/pregunta_completa/justificacion: {e}\nRespuesta RAW del LLM:\n{respuesta_llm}")
        justificacion = f"Error al parsear la respuesta del LLM: {e}"


    print(f"\n--- [🔍 CLASIFICADOR] DEBUGGING INFO ---") 
    print(f"[🔍 CLASIFICADOR] Prompt enviado al LLM:\n{prompt}") 
    print(f"[🔍 CLASIFICADOR] Respuesta RAW del LLM:\n{respuesta_llm}")
    print(f"[🔍 CLASIFICADOR] Pregunta original: {pregunta_original}")
    print(f"[🔍 CLASIFICADOR] Pregunta completa generada: {pregunta_completa}")
    print(f"[🔍 CLASIFICADOR] Tipo detectado: {tipo}")
    print(f"[🔍 CLASIFICADOR] Justificación: {justificacion}")
    print(f"--- [🔍 CLASIFICADOR] FIN DEBUGGING INFO ---\n")

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
# 6. Nodo: Series temporales
# ---------------------------------------------------------

def analizar_series_temporales(state: ChatbotState) -> ChatbotState:
    pregunta_original = state["input"]
    pregunta_completa = state["pregunta_completa"]
    fecha_actual = state.get("fecha_actual", datetime.now().strftime("%Y-%m-%d"))
    print(f"[📊 SERIES] Analizando series temporales con:\n   Original: '{pregunta_original}'\n   Completa: '{pregunta_completa}'\n   Fecha Actual: '{fecha_actual}'")

    prompt = PROMPT_SERIES.format(
        pregunta_original=pregunta_original,
        pregunta_completa=pregunta_completa,
        fecha_actual=fecha_actual
    )
    response = llm.invoke(prompt)
    try:
        data = extract_json(response.content)
    except Exception as e:
        print(f"⚠️ Error extrayendo JSON del LLM en nodo Series Temporales: {e}")
        return {
            **state,
            "respuesta": "❌ No se pudo extraer la información necesaria para la predicción de series temporales.",
            "fuente": "series_temporales",
            "grafico_base64": None # Ensure it's None on error
        }

    empresa = data.get("empresa", "BBVA").upper()
    lag = int(data.get("lag", 1))
    respuesta_simulada = data.get("respuesta", "")

    print(f"[📊 SERIES] Empresa detectada: {empresa}, lag: {lag}")
    print(f"[📊 SERIES] Respuesta simulada (del LLM): {respuesta_simulada}")

    modelos_dir = os.path.join(os.getcwd(), "modelos_por_empresa")
    path_csv = os.path.join(os.getcwd(), "data/IBEX35_cotizaciones_20_Limpio.csv")

    resultado = ejecutar_prediccion(empresa, lag, path_csv, modelos_dir)
    respuesta_real_modelo = resultado.get("respuesta", "No se pudo obtener la predicción real.")
    grafico_base64 = resultado.get("grafico_base64", None) # <--- GET THE BASE64 STRING HERE

    final_respuesta = respuesta_real_modelo if "No se pudo obtener" not in respuesta_real_modelo else respuesta_simulada

    return {
        **state,
        "respuesta": final_respuesta,
        "fuente": "series_temporales",
        "empresa": empresa,
        "grafico_base64": grafico_base64 # <--- ADD IT TO THE STATE HERE
    }

# ---------------------------------------------------------
# 7. Nodo: Documentos financieros 
# ---------------------------------------------------------

def consulta_qdrant(state: ChatbotState) -> ChatbotState:
    pregunta_original = state["input"]
    pregunta_completa = state["pregunta_completa"] 
    fecha_actual = state.get("fecha_actual", datetime.now().strftime("%Y-%m-%d")) 
    print(f"\n[📚 Nodo RAG] ✅ Entrada al nodo 'consulta_qdrant' con:\n   Original: '{pregunta_original}'\n   Completa: '{pregunta_completa}'\n   Fecha Actual: '{fecha_actual}'")

    # Inicializar o recuperar datos_empresa_cache
    datos_empresa_cache = state.get("datos_empresa_cache", {})
    
    try:
        print("[📚 Nodo RAG] Buscando fragmentos en Qdrant...")
        resultados = buscar_en_qdrant(pregunta_completa) 

        fragmentos = [r.payload.get("resumen", "") for r in resultados if hasattr(r, 'payload') and r.payload and r.payload.get("resumen")]
        
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

        prompt_rag = PROMPT_RAG_DOCUMENTOS.format(
            contexto=contexto,
            pregunta_original=pregunta_original,
            pregunta_completa=pregunta_completa,
            fecha_actual=fecha_actual 
        )
        print(f"[📚 Nodo RAG] Prompt RAG enviado al LLM (primeros 500 chars):\n'{prompt_rag[:500]}...'")

        print("[📚 Nodo RAG] Invocando LLM para generar respuesta RAG...")
        llm_response_object = llm.invoke(prompt_rag)
        llm_response_raw = llm_response_object.content.strip()
        print(f"[📚 Nodo RAG] Respuesta RAW del LLM:\n'{llm_response_raw}'")

        respuesta_final_text = llm_response_raw
        respuesta_final_text = respuesta_final_text.replace(". ", ". \n").replace("- ", "• ")

        print(f"[📚 Nodo RAG] ✅ Respuesta final generada (primeros 500 chars):\n'{respuesta_final_text[:500]}...'")

        # --- NUEVO: Intentar extraer datos estructurados de la respuesta RAG para cache ---
        # Esto es un paso CRÍTICO. Si la respuesta RAG contiene un dato específico
        # (ej. "Los beneficios de BBVA en 2023 fueron X"), necesitamos extraerlo aquí.
        # Esto requerirá un sub-LLM o regex inteligente para extraer el valor.
        # Por ahora, un ejemplo muy simplificado si buscas beneficios:
        
        empresa_preguntada = None
        # Primero, intenta identificar la empresa principal en la pregunta (si solo hay una)
        for empresa_ibex in [
            "bbva", "repsol", "iberdrola", "santander", "telefonica", "acciona",
            "acciona energia", "acerinox", "acs", "aena", "amadeus", "arcelormittal",
            "bankinter", "caixabank", "cellnex telecom", "enagas", "endesa",
            "ferrovial", "fluidra", "grifols", "iag", "inditex", "indra",
            "inm. colonial", "laboratorios farma (rovi)", "logista", "mapfre",
            "merlin properties", "naturgy", "puig", "ree", "sabadell", "sacyr",
            "solaria energia", "unicaja banco"
        ]:
            if empresa_ibex in pregunta_completa.lower():
                empresa_preguntada = empresa_ibex
                break

        if empresa_preguntada:
            # Ejemplo: Extraer beneficios si la pregunta es sobre "beneficios" y la respuesta RAG los contiene
            if "beneficios" in pregunta_completa.lower() or "ebitda" in pregunta_completa.lower():
                # Puedes usar otro LLM call o regex aquí para extraer el número
                # Por simplicidad, un regex muy básico:
                match_beneficios = re.search(r"(\d[\d\.,]+)\s*(millones|miles de millones|€)", respuesta_final_text, re.IGNORECASE)
                if match_beneficios:
                    valor_str = match_beneficios.group(1).replace('.', '').replace(',', '.') # Convertir a formato numérico
                    unidad = match_beneficios.group(2).lower()
                    try:
                        valor_num = float(valor_str)
                        if "miles de millones" in unidad:
                            valor_num *= 1_000 # Convertir a millones si es el caso
                        elif "millones" in unidad:
                            valor_num *= 1 # Ya está en millones
                        
                        # Guardar en cache: {empresa: {metrica: {valor: X, unidad: Y, periodo: Z}}}
                        if empresa_preguntada not in datos_empresa_cache:
                            datos_empresa_cache[empresa_preguntada] = {}
                        
                        # Se necesita identificar qué periodo de tiempo es (ej. 2023)
                        periodo_match = re.search(r"\b(20\d{2})\b", pregunta_completa) # Busca un año
                        periodo = periodo_match.group(1) if periodo_match else "desconocido"

                        datos_empresa_cache[empresa_preguntada][f"beneficios_{periodo}"] = {
                            "valor": valor_num, 
                            "unidad": "millones €", 
                            "periodo": periodo
                        }
                        print(f"[📚 Nodo RAG] Datos estructurados extraídos y cacheado para {empresa_preguntada}: {datos_empresa_cache[empresa_preguntada][f'beneficios_{periodo}']}")
                    except ValueError:
                        print(f"[📚 Nodo RAG] No se pudo convertir el valor '{valor_str}' a número.")

        return {
            **state,
            "respuesta": respuesta_final_text,
            "fuente": "qdrant",
            "fragmentos": fragmentos,
            "datos_empresa_cache": datos_empresa_cache # Actualizar el cache en el estado
        }

    except Exception as general_e:
        print(f"❌ Error CRÍTICO y general en el nodo Qdrant: {general_e}")
        return {
            **state,
            "respuesta": f"Lo siento mucho, hubo un problema técnico inesperado al procesar tu solicitud de documentos financieros. Detalles: {general_e}. Por favor, inténtalo de nuevo o formula la pregunta de otra manera.",
            "fuente": "error_qdrant",
            "fragmentos": [],
            "datos_empresa_cache": datos_empresa_cache # Asegurar que el cache se pase incluso en error
        }

# ---------------------------------------------------------
# 8. Nodo: Consulta API financiera 
# ---------------------------------------------------------

def consultar_api_financiera(state: ChatbotState) -> ChatbotState:
    pregunta_original = state["input"]
    pregunta_para_api_extraccion = state["pregunta_completa"]
    fecha_actual = state["fecha_actual"] 
    print(f"[🌐 Nodo API] Pregunta original para extracción: {pregunta_original}")
    print(f"[🌐 Nodo API] Pregunta completa para extracción: {pregunta_para_api_extraccion}")
    print(f"[🌐 Nodo API] Fecha actual (del estado): {fecha_actual}")

    # Inicializar o recuperar datos_empresa_cache
    datos_empresa_cache = state.get("datos_empresa_cache", {})

    extraction_prompt = PROMPT_API_EXTRAER.format(
        pregunta_original=pregunta_original,
        pregunta_completa=pregunta_para_api_extraccion,
        fecha_actual=fecha_actual 
    )
    
    print(f"[🌐 Nodo API] Prompt de extracción:\n{extraction_prompt}")
    
    response = llm.invoke(extraction_prompt)
    llm_response_content = response.content.strip()
    
    print(f"[🌐 Nodo API] Respuesta LLM para extracción CRUDA:\n'{llm_response_content}'")
    
    empresa_normalizada = None
    fecha_inicio = None
    fecha_fin = None
    
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
        # No se retorna, se continúa para dar un mensaje de error más específico si faltan parámetros.


    if not all([empresa_normalizada, fecha_inicio, fecha_fin]):
        print(f"⚠️ Faltan parámetros clave: empresa={empresa_normalizada}, fecha_inicio={fecha_inicio}, fecha_fin={fecha_fin}")
        return {
            **state,
            "respuesta": "❌ Faltan parámetros clave: empresa, fecha de inicio o fin. Por favor, sé más específico.",
            "fuente": "api",
            "datos_empresa_cache": datos_empresa_cache # Asegurar que el cache se pase incluso en error
        }

    resultado = construir_respuesta_yfinance(empresa_normalizada, fecha_inicio, fecha_fin)
    print(f"[🌐 Nodo API] Resultado de la API financiera:\n{resultado.get('respuesta', 'N/A')}")

    # --- Guardar el precio medio en el cache ---
    precio_medio = resultado.get("precio_medio") # Asume que construir_respuesta_yfinance devuelve 'precio_medio'
    if precio_medio is not None and empresa_normalizada:
        if empresa_normalizada not in datos_empresa_cache:
            datos_empresa_cache[empresa_normalizada] = {}
        
        # Usar la fecha_fin como identificador para este punto de datos
        datos_empresa_cache[empresa_normalizada][f"precio_cierre_{fecha_fin}"] = {
            "valor": precio_medio, 
            "unidad": "€", 
            "periodo": fecha_fin # O el rango de fechas
        }
        print(f"[🌐 Nodo API] Precio medio cacheado para {empresa_normalizada}: {precio_medio}")


    return {
        **state,
        "respuesta": resultado.get('respuesta', "No se pudo obtener el precio."),
        "fuente": "api",
        "empresa": empresa_normalizada,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "datos_empresa_cache": datos_empresa_cache # Actualizar el cache en el estado
    }

# ---------------------------------------------------------
# 9. Nodo: Actualizar Historial Completo
# ---------------------------------------------------------

def actualizar_historial_final(state: ChatbotState) -> ChatbotState:
    historial_completo_previo = state.get("historial_completo", [])
    
    nueva_entrada = {
        "pregunta_usuario": state["input"],
        "pregunta_procesada": state.get("pregunta_completa", state["input"]),
        "respuesta_asistente": state.get("respuesta", "No se pudo generar una respuesta."),
        "fuente": state.get("fuente", "desconocida"),
        "timestamp": datetime.now().isoformat(),
        "datos_generados": state.get("datos_recopilados", {}) 
    }
    
    historial_completo_actualizado = historial_completo_previo + [nueva_entrada]

    historial_completo_actualizado = historial_completo_actualizado[-10:] 

    print(f"[🔄 HISTORIAL] Historial completo actualizado. Total entradas: {len(historial_completo_actualizado)}")
    print(f"[🔄 HISTORIAL] Última entrada: {nueva_entrada}")

    return {
        **state,
        "historial_completo": historial_completo_actualizado
    }


# ---------------------------------------------------------
# 10. Construcción del grafo 
# ---------------------------------------------------------

def build_graph():
    graph = StateGraph(ChatbotState)
    graph.add_node("clasificar", RunnableLambda(clasificar_intencion))
    graph.add_node("series_temporales", RunnableLambda(analizar_series_temporales))
    graph.add_node("consulta_qdrant", RunnableLambda(consulta_qdrant))
    graph.add_node("consulta_api", RunnableLambda(consultar_api_financiera))
    graph.add_node("actualizar_historial", RunnableLambda(actualizar_historial_final)) 

    graph.set_entry_point("clasificar")

    graph.add_conditional_edges("clasificar", seleccionar_fuente, {
        "series_temporales": "series_temporales",
        "documentos_financieros": "consulta_qdrant",
        "consulta_api": "consulta_api",
        # Eliminada la rama "comparacion_financiera"
    })

    graph.add_edge("series_temporales", "actualizar_historial")
    graph.add_edge("consulta_qdrant", "actualizar_historial")
    graph.add_edge("consulta_api", "actualizar_historial")
    # Eliminada la conexión desde "generar_comparacion"
    
    graph.add_edge("actualizar_historial", END)

    return graph.compile()

graph = build_graph()

# ---------------------------------------------------------
# 11. Función principal para interactuar con el chatbot
# ---------------------------------------------------------

def chatbot_response(user_input: str, current_state: Optional[ChatbotState] = None) -> ChatbotState:
    if current_state is None:
        current_state = ChatbotState(
            input=user_input,
            historial_preguntas=[],
            historial_completo=[],
            fecha_actual=datetime.now().strftime("%Y-%m-%d"),
            datos_empresa_cache={} # Inicializa el cache vacío
        )
    else:
        current_state["input"] = user_input
        current_state["fecha_actual"] = datetime.now().strftime("%Y-%m-%d")

    final_state = graph.invoke(current_state) 
    return final_state

if __name__ == "__main__":
    print("🔎 Chatbot Financiero IBEX 35 - Modo Interactivo")
    print("Escribe tus preguntas una por una. Escribe 'salir' para terminar.\n")

    current_chat_state: Optional[ChatbotState] = None

    # Test cases as requested
    test_questions = [
        "¿Cuál fue el precio de BBVA ayer?",
        "¿Y el de Bankinter?",
        "¿Qué beneficio neto atribuido obtuvo Iberdrola en 2024 y cómo evolucionó respecto al año anterior?",
        "¿Cuáles son los tres ejes del nuevo plan estratégico de Bankinter para el periodo 2024–2026?"

    ]

    for i, user_question in enumerate(test_questions):
        print(f"\n\n--- PREGUNTA DE PRUEBA {i+1}: {user_question} ---")
        if current_chat_state is None:
            current_chat_state = ChatbotState(
                input=user_question,
                historial_preguntas=[],
                historial_completo=[],
                fecha_actual=datetime.now().strftime("%Y-%m-%d"),
                datos_empresa_cache={}
            )
        else:
            current_chat_state["input"] = user_question
            current_chat_state["fecha_actual"] = datetime.now().strftime("%Y-%m-%d")

        try:
            result_state = graph.invoke(current_chat_state)

            print("\n✅ Respuesta generada:")
            print(result_state.get("respuesta", "❌ No se generó ninguna respuesta."))

            print("\n📊 Detalles del estado:")
            print(f"- Clasificación: {result_state.get('tipo_pregunta', 'No detectada')}")
            print(f"- Empresa: {result_state.get('empresa', 'No detectada')}")
            print(f"- Fuente: {result_state.get('fuente', 'No disponible')}")
            print(f"- Fechas: {result_state.get('fecha_inicio')} -> {result_state.get('fecha_fin')}")
            print(f"- Pregunta completa: {result_state.get('pregunta_completa', '')}")
            print(f"- Historial: {result_state.get('historial_preguntas', [])}")
            print(f"- Cache de Datos (último estado): {json.dumps(result_state.get('datos_empresa_cache', {}), indent=2)}")

            # Update the state for the next question
            current_chat_state = result_state

        except Exception as e:
            print(f"\n❌ Error en el procesamiento del chatbot: {e}")
            print("🔁 Por favor, intenta con otra pregunta.\n")
    
    # You can continue with interactive mode after the test questions if you want
    print("\n--- FIN DE PRUEBAS AUTOMÁTICAS ---")
    print("Puedes seguir preguntando en modo interactivo si lo deseas. Escribe 'salir' para terminar.")
    
    while True:
        user_question = input("\n🧠 Tu pregunta: ").strip()
        if user_question.lower() in {"salir", "exit", "quit"}:
            print("👋 Terminando la sesión. ¡Hasta la próxima!")
            break

        if current_chat_state is None:
            current_chat_state = ChatbotState(
                input=user_question,
                historial_preguntas=[],
                historial_completo=[],
                fecha_actual=datetime.now().strftime("%Y-%m-%d"),
                datos_empresa_cache={}
            )
        else:
            current_chat_state["input"] = user_question
            current_chat_state["fecha_actual"] = datetime.now().strftime("%Y-%m-%d")

        try:
            result_state = graph.invoke(current_chat_state)

            print("\n✅ Respuesta generada:")
            print(result_state.get("respuesta", "❌ No se generó ninguna respuesta."))

            print("\n📊 Detalles del estado:")
            print(f"- Clasificación: {result_state.get('tipo_pregunta', 'No detectada')}")
            print(f"- Empresa: {result_state.get('empresa', 'No detectada')}")
            print(f"- Fuente: {result_state.get('fuente', 'No disponible')}")
            print(f"- Fechas: {result_state.get('fecha_inicio')} -> {result_state.get('fecha_fin')}")
            print(f"- Pregunta completa: {result_state.get('pregunta_completa', '')}")
            print(f"- Historial: {result_state.get('historial_preguntas', [])}")
            print(f"- Cache de Datos (último estado): {json.dumps(result_state.get('datos_empresa_cache', {}), indent=2)}")


            current_chat_state = result_state

        except Exception as e:
            print(f"\n❌ Error en el procesamiento del chatbot: {e}")
            print("🔁 Por favor, intenta con otra pregunta.\n")