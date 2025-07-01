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
from prompts import PROMPT_SERIES, PROMPT_API_EXTRAER, PROMPT_CLASIFICACION, PROMPT_RAG_DOCUMENTOS, PROMPT_COMPARACION
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
    temperature=0.0
)

# ---------------------------------------------------------
# 2. Estado del chatbot - ¡ACTUALIZADO!
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


def extract_json(text: str) -> Dict[str, Any]:
    try:
        # 1. Busca bloque JSON con triple backtick
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
        if json_match:
            json_text = json_match.group(1)
        else:
            # 2. Busca el primer bloque {...}
            matches = re.findall(r"\{.*?\}", text, re.DOTALL)
            if not matches:
                raise ValueError("No se encontró un bloque JSON en el texto.")
            json_text = matches[0]

        return json.loads(json_text)
    except Exception as e:
        raise ValueError(f"Error al extraer JSON: {e}\nTexto recibido:\n{text}")
    

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
        
        categorias_validas = {"series_temporales", "documentos_financieros", "consulta_api", "comparacion_financiera"}
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
    print(f"[📊 SERIES] Analizando series temporales con:\n   Original: '{pregunta_original}'\n   Completa: '{pregunta_completa}'\n   Fecha Actual: '{fecha_actual}'")

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
            "fuente": "series_temporales"
        }

    empresa = data.get("empresa", "BBVA").upper()
    lag = int(data.get("lag", 1))
    respuesta_simulada = data.get("respuesta", "")

    print(f"[📊 SERIES] Empresa detectada: {empresa}, lag: {lag}")
    print(f"[📊 SERIES] Respuesta simulada (del LLM): {respuesta_simulada}")

    modelos_dir = os.path.join(os.getcwd(), "modelos_por_empresa")
    path_csv = os.path.join(os.getcwd(), "IBEX35_cotizaciones_20_Limpio.csv")

    resultado = ejecutar_prediccion(empresa, lag, path_csv, modelos_dir)
    respuesta_real_modelo = resultado.get("respuesta", "No se pudo obtener la predicción real.")
    
    final_respuesta = respuesta_real_modelo if "No se pudo obtener" not in respuesta_real_modelo else respuesta_simulada

    return {
        **state,
        "respuesta": final_respuesta,
        "fuente": "series_temporales",
        "empresa": empresa
    }

# ---------------------------------------------------------
# 7. Nodo: Documentos financieros -> Qdrant - ¡ACTUALIZADO!
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

        fragmentos = [r.payload.get("fragmento", "") for r in resultados if hasattr(r, 'payload') and r.payload and r.payload.get("fragmento")]
        
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
        
        # Primero, intenta identificar la empresa principal en la pregunta (si solo hay una)
        empresa_preguntada = None
        for empresa_ibex in ["bbva", "repsol", "iberdrola", "santander", "telefonica", "acciona"]: # Lista de empresas conocidas
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
# 8. Nodo: Consulta API financiera - ¡ACTUALIZADO!
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

    # --- NUEVO: Guardar el precio medio en el cache ---
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
# 9. Nodo: Generar Comparación - ¡SIMPLIFICADO!
# ---------------------------------------------------------

def generar_comparacion(state: ChatbotState) -> ChatbotState:
    """
    Genera una comparación utilizando únicamente el historial de la conversación
    y la pregunta completa del usuario, basándose en lo que el modelo ya ha respondido.
    """
    pregunta_completa = state["pregunta_completa"]
    historial_completo = state.get("historial_completo", [])
    
    print(f"\n[🤝 Nodo COMPARACION] Iniciando comparación para: '{pregunta_completa}'")

    # Verifica si hay suficiente historial para realizar una comparación
    if not historial_completo or len(historial_completo) < 1:
        return {
            **state,
            "respuesta": "Lo siento, necesito más contexto para realizar una comparación. Por favor, haz primero algunas preguntas sobre los temas o empresas que te interesan.",
            "fuente": "comparacion",
        }

    # 1. Construye el contexto a partir del historial de conversación.
    # Esto representa "lo que ya ha respondido el modelo".
    contexto_historial = []
    for turno in historial_completo:
        pregunta_usuario = turno.get("pregunta_usuario", "N/A")
        respuesta_asistente = turno.get("respuesta_asistente", "N/A")
        # Se formatea cada turno para que el LLM entienda el flujo de la conversación
        contexto_historial.append(
            f"- El usuario preguntó: '{pregunta_usuario}'\n- El asistente respondió: '{respuesta_asistente}'"
        )
    
    contexto_para_llm = "\n\n".join(contexto_historial)
    print(f"[🤝 Nodo COMPARACION] Contexto construido a partir del historial para el LLM.")

    # 2. Invoca al LLM con el prompt de comparación y el contexto del historial.
    prompt_comparacion = PROMPT_COMPARACION.format(
        pregunta_completa=pregunta_completa,
        historial_conversacion=contexto_para_llm
    )

    print(f"[🤝 Nodo COMPARACION] Enviando prompt al LLM para generar la comparación.")
    llm_response = llm.invoke(prompt_comparacion)
    respuesta_comparativa = llm_response.content.strip()
    
    print(f"[🤝 Nodo COMPARACION] Respuesta comparativa generada.")

    # 3. Devuelve el estado actualizado con la respuesta.
    return {
        **state,
        "respuesta": respuesta_comparativa,
        "fuente": "comparacion",
        # No se modifican 'datos_recopilados' ni 'datos_empresa_cache',
        # simplemente se pasan como estaban.
    }
# ---------------------------------------------------------
# 10. Nodo: Actualizar Historial Completo
# ---------------------------------------------------------

def actualizar_historial_final(state: ChatbotState) -> ChatbotState:
    historial_completo_previo = state.get("historial_completo", [])
    
    nueva_entrada = {
        "pregunta_usuario": state["input"],
        "pregunta_procesada": state.get("pregunta_completa", state["input"]),
        "respuesta_asistente": state.get("respuesta", "No se pudo generar una respuesta."),
        "fuente": state.get("fuente", "desconocida"),
        "timestamp": datetime.now().isoformat(),
        # También guardar los datos estructurados que se procesaron en esta iteración
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
# 11. Construcción del grafo 
# ---------------------------------------------------------

def build_graph():
    graph = StateGraph(ChatbotState)
    graph.add_node("clasificar", RunnableLambda(clasificar_intencion))
    graph.add_node("series_temporales", RunnableLambda(analizar_series_temporales))
    graph.add_node("consulta_qdrant", RunnableLambda(consulta_qdrant))
    graph.add_node("consulta_api", RunnableLambda(consultar_api_financiera))
    graph.add_node("generar_comparacion", RunnableLambda(generar_comparacion)) 
    graph.add_node("actualizar_historial", RunnableLambda(actualizar_historial_final)) 

    graph.set_entry_point("clasificar")

    graph.add_conditional_edges("clasificar", seleccionar_fuente, {
        "series_temporales": "series_temporales",
        "documentos_financieros": "consulta_qdrant",
        "consulta_api": "consulta_api",
        "comparacion_financiera": "generar_comparacion" 
    })

    graph.add_edge("series_temporales", "actualizar_historial")
    graph.add_edge("consulta_qdrant", "actualizar_historial")
    graph.add_edge("consulta_api", "actualizar_historial")
    graph.add_edge("generar_comparacion", "actualizar_historial") 
    
    graph.add_edge("actualizar_historial", END)

    return graph.compile()

graph = build_graph()

# ---------------------------------------------------------
# 12. Función principal para interactuar con el chatbot
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

    while True:
        user_question = input("🧠 Tu pregunta: ").strip()
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
            print(f"- Fechas: {result_state.get('fecha_inicio')} → {result_state.get('fecha_fin')}")
            print(f"- Pregunta completa: {result_state.get('pregunta_completa', '')}")
            print(f"- Historial: {result_state.get('historial_preguntas', [])}")

            # Actualiza el estado para la siguiente pregunta
            current_chat_state = result_state

        except Exception as e:
            print(f"\n❌ Error en el procesamiento del chatbot: {e}")
            print("🔁 Por favor, intenta con otra pregunta.\n")

    
    # Puedes añadir aquí un bucle interactivo si quieres que el usuario siga preguntando
    # while True:
    #     user_question_manual = input("\nTu pregunta (o 'salir'): ")
    #     if user_question_manual.lower() == 'salir':
    #         print("¡Hasta luego!")
    #         break
    #     
    #     current_chat_state["input"] = user_question_manual
    #     current_chat_state["fecha_actual"] = datetime.now().strftime("%Y-%m-%d")
    #     
    #     try:
    #         result_state = graph.invoke(current_chat_state)
    #         print(f"\nRespuesta del bot: {result_state.get('respuesta', 'Lo siento, no pude procesar tu solicitud.')}")
    #         current_chat_state = result_state
    #     except Exception as e:
    #         print(f"Ocurrió un error en el chatbot: {e}")
    #         print("Por favor, inténtalo de nuevo.")
    #"¿Cuál fue el precio de BBVA ayer?",
     #   "¿Y el de Bankinter?",
      #  "Compara ambas.",
       # "¿Qué beneficios obtuvo Repsol en 2023?",
        #"¿Cómo se espera que evolucione Iberdrola la próxima semana?"