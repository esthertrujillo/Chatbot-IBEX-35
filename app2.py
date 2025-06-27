import streamlit as st
from main_graph import graph # Asumiendo que main_graph es el nombre de tu archivo main.py
import torch
torch.classes = None  # Para evitar conflictos si usas Groq + LangChain

# Configurar la página
st.set_page_config(page_title="Chatbot IBEX 35", page_icon="💬", layout="centered")

st.title("🤖 Chatbot Financiero IBEX 35")
st.caption("Consulta precios históricos del IBEX 35 o analiza textos financieros con lenguaje natural.")

# Inicializar historial de la conversación
if "historial" not in st.session_state:
    st.session_state.historial = []

# Mostrar el historial de mensajes como conversación
for mensaje in st.session_state.historial:
    rol = mensaje["role"]
    contenido = mensaje["content"]
    with st.chat_message(rol):
        st.markdown(contenido)

# Entrada del usuario en modo chat
if prompt := st.chat_input("Escribe tu consulta financiera..."):
    # Mostrar el mensaje del usuario
    st.chat_message("user").markdown(prompt)
    st.session_state.historial.append({"role": "user", "content": prompt})

    # --- Lógica para limitar el historial (después de añadir el mensaje del usuario) ---
    # Queremos mantener 3 preguntas y 3 respuestas (un total de 6 mensajes)
    # Si el historial supera los 6 mensajes, nos quedamos con los últimos 6.
    # Esto asegura que el historial pasado al grafo ya esté limitado.
    if len(st.session_state.historial) > 6:
        st.session_state.historial = st.session_state.historial[-6:]
    # --- Fin de la lógica para limitar el historial ---

    try:
        # Pasa el historial de la conversación (ya limitado) al grafo
        initial_state = {
            "input": prompt,
            "historial_conversacion": st.session_state.historial, # Aquí se pasa el historial limitado
            "empresa": None,
            "tipo_pregunta": None,
            "respuesta": None,
            "fuente": None,
            "fecha_inicio": None,
            "fecha_fin": None,
            "grafico_base64": None
        }
        result = graph.invoke(initial_state) # Invoca el grafo con el estado actualizado
        
        respuesta = result.get("respuesta", "Sin respuesta generada.")
        fuente = result.get("fuente", "desconocida")

        with st.chat_message("assistant"):
            st.markdown(f"**Fuente: {fuente}**\n\n{respuesta}")

            # Mostrar gráfico si aplica
            if fuente == "series_temporales" and result.get("grafico_base64"):
                st.image("data:image/png;base64," + result["grafico_base64"], caption="📈 Gráfico de evolución")

            # Mostrar fragmentos si es una respuesta RAG
            if fuente == "qdrant" and result.get("fragmentos"):
                with st.expander("🔍 Fragmentos usados por el sistema"):
                    for frag in result["fragmentos"]:
                        st.markdown(f"- {frag}")

        # Guardar respuesta del bot en el historial
        st.session_state.historial.append({"role": "assistant", "content": f"**Fuente: {fuente}**\n\n{respuesta}"})

        # --- Lógica para limitar el historial (después de añadir la respuesta del bot) ---
        # Asegurarse de que el historial no exceda los 6 mensajes después de añadir la respuesta del asistente
        if len(st.session_state.historial) > 6:
            st.session_state.historial = st.session_state.historial[-6:]
        # --- Fin de la lógica para limitar el historial ---

    except Exception as e:
        error_msg = f"⚠️ Error procesando la consulta: {e}"
        st.chat_message("assistant").markdown(error_msg)
        st.session_state.historial.append({"role": "assistant", "content": error_msg})

        # También limitar el historial en caso de error, para mantener la coherencia
        if len(st.session_state.historial) > 6:
            st.session_state.historial = st.session_state.historial[-6:]