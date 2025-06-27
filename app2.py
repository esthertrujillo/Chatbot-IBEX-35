import streamlit as st
import torch
import re # Importar re para la extracción de historial de preguntas
from main_graph import graph # Asumiendo que main_graph es el nombre de tu archivo main.py

# Para evitar conflictos si usas Groq + LangChain
torch.classes = None

# Configurar la página de Streamlit
st.set_page_config(page_title="Chatbot IBEX 35", page_icon="💬", layout="centered")

st.title("🤖 Chatbot Financiero IBEX 35")
st.caption("Consulta precios históricos, realiza predicciones o analiza documentos financieros del IBEX 35.")

# Inicializar los historiales en st.session_state
if "historial_display" not in st.session_state:
    # Historial para mostrar en la interfaz (preguntas y respuestas)
    st.session_state.historial_display = []
if "historial_preguntas_llm" not in st.session_state:
    # Historial de solo las últimas 3 preguntas del usuario para pasar al LLM
    st.session_state.historial_preguntas_llm = []
if "historial_completo_grafo" not in st.session_state:
    # Historial completo gestionado por el grafo (preguntas originales + procesadas + respuestas)
    st.session_state.historial_completo_grafo = []

# Mostrar el historial de mensajes en la interfaz de Streamlit
for mensaje in st.session_state.historial_display:
    rol = mensaje["role"]
    contenido = mensaje["content"]
    with st.chat_message(rol):
        st.markdown(contenido)

# Entrada del usuario en modo chat
if prompt := st.chat_input("Escribe tu consulta financiera..."):
    # Mostrar el mensaje del usuario inmediatamente
    st.chat_message("user").markdown(prompt)
    st.session_state.historial_display.append({"role": "user", "content": prompt})

    try:
        # Preparar el estado inicial para el grafo
        # 'input' es la pregunta original del usuario para el nodo clasificador
        # 'historial_preguntas' es la lista de las últimas 3 preguntas del usuario para el clasificador
        # 'historial_completo' es el historial detallado gestionado por el grafo y persistido entre turnos
        initial_state = {
            "input": prompt,
            "historial_preguntas": st.session_state.historial_preguntas_llm,
            "historial_completo": st.session_state.historial_completo_grafo,
            "empresa": None,
            "tipo_pregunta": None,
            "respuesta": None,
            "fuente": None,
            "fecha_inicio": None,
            "fecha_fin": None,
            "grafico_base64": None,
            "pregunta_completa": None # El grafo la generará
        }

        # Invocar el grafo con el estado actualizado
        result = graph.invoke(initial_state)
        
        # Extraer la respuesta y la fuente del resultado del grafo
        respuesta = result.get("respuesta", "Lo siento, no pude generar una respuesta.")
        fuente = result.get("fuente", "desconocida")
        
        # Mostrar la respuesta del bot
        with st.chat_message("assistant"):
            st.markdown(f"**Fuente: {fuente}**\n\n{respuesta}")

            # Mostrar gráfico si aplica (si lo implementas en el nodo de series temporales y lo pasas)
            if fuente == "series_temporales" and result.get("grafico_base64"):
                st.image("data:image/png;base64," + result["grafico_base64"], caption="📈 Gráfico de evolución")

            # Mostrar fragmentos si es una respuesta RAG
            if fuente == "qdrant" and result.get("fragmentos"):
                with st.expander("🔍 Fragmentos usados por el sistema"):
                    for i, frag in enumerate(result["fragmentos"]):
                        # Limitar la longitud de los fragmentos para no saturar la interfaz
                        display_frag = frag[:300] + "..." if len(frag) > 300 else frag
                        st.markdown(f"- {display_frag}")

        # --- Actualizar los historiales en st.session_state después de la respuesta del asistente ---
        # 1. Actualizar historial para display
        st.session_state.historial_display.append({"role": "assistant", "content": f"**Fuente: {fuente}**\n\n{respuesta}"})
        
        # 2. Actualizar historial de solo preguntas para el LLM (últimas 3)
        # Esto asegura que solo las preguntas del usuario se pasen para el contexto de la próxima clasificación
        st.session_state.historial_preguntas_llm.append(prompt)
        st.session_state.historial_preguntas_llm = st.session_state.historial_preguntas_llm[-3:] # Limitar a las últimas 3

        # 3. Actualizar historial completo del grafo
        # El grafo ya lo maneja internamente, solo recuperamos el estado final actualizado
        st.session_state.historial_completo_grafo = result.get("historial_completo", [])

        # Opcional: Mostrar la pregunta completa para depuración
        # if result.get("pregunta_completa"):
        #     st.markdown(f"*(Debug - Pregunta Completa: {result['pregunta_completa']})*")

    except Exception as e:
        error_msg = f"⚠️ Ocurrió un error inesperado al procesar tu consulta: {e}"
        st.chat_message("assistant").markdown(error_msg)
        st.session_state.historial_display.append({"role": "assistant", "content": error_msg})
