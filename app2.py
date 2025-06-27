import streamlit as st
from main_graph import graph # Asumiendo que main_graph es tu archivo con el grafo
from datetime import datetime
import time # Importado para el efecto de "escribiendo"

def main():
    """
    Función principal que renderiza la aplicación de chatbot en Streamlit.
    """
    # --- 1. CONFIGURACIÓN DE LA PÁGINA ---
    # Usamos 'wide' para dar más espacio al banner y al contenido.
    st.set_page_config(page_title="Chatbot Financiero IBEX 35", page_icon="📈", layout="wide")

    # --- 2. BARRA LATERAL (SIDEBAR) ---
    with st.sidebar:
        st.title("ℹ️ Acerca del Chatbot")
        st.info(
            "Este chatbot te permite interactuar con datos del IBEX 35. "
            "Puedes pedir precios históricos, análisis de documentos (RAG) o predicciones futuras."
        )

        st.warning(
            "**Aviso:** Este es un chatbot experimental. "
            "La información proporcionada no constituye asesoramiento financiero."
        )

        st.divider()

        # Botón para limpiar el historial del chat
        if st.button("🗑️ Limpiar Historial del Chat"):
            # Limpiamos todas las variables de estado de la sesión
            st.session_state.historial_display = []
            st.session_state.historial_preguntas_llm = []
            st.session_state.historial_completo_grafo = []
            # Recargamos la página para que el cambio sea visible inmediatamente
            st.rerun()

    # --- 3. INTERFAZ PRINCIPAL ---

# AHORA: Usamos columnas para centrar y reducir el tamaño del logo
    col1, col2, col3 = st.columns([2.5, 1, 2.5])  # [Espacio Izquierda, Logo, Espacio Derecha]
    with col2:
        st.image("utils/png.jpg") # El logo se mostrará en la columna central (más estrecha)

    st.title("Chatbot Financiero del IBEX 35")
    st.caption("Consulta precios, analiza documentos o pide predicciones del mercado español.")

    # Inicializar los historiales en st.session_state si no existen
    if "historial_display" not in st.session_state:
        st.session_state.historial_display = []
    if "historial_preguntas_llm" not in st.session_state:
        st.session_state.historial_preguntas_llm = []
    if "historial_completo_grafo" not in st.session_state:
        st.session_state.historial_completo_grafo = []

    # --- 4. MENSAJE DE BIENVENIDA Y EJEMPLOS (si el chat está vacío) ---
    if not st.session_state.historial_display:
        with st.container(border=True, height=200):
            st.write("👋 **¡Hola! ¿En qué puedo ayudarte hoy?**")
            st.write("Puedes probar con alguna de estas opciones:")
            
            # Usamos columnas para los botones de ejemplo
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Dame el precio de Telefónica ayer"):
                    st.session_state.prompt_from_button = "Dame el precio de Telefónica ayer"
                    st.rerun()
            with col2:
                if st.button("¿Cuál es la opinión sobre Repsol?"):
                    st.session_state.prompt_from_button = "¿Cuál es la opinión sobre Repsol según los últimos informes?"
                    st.rerun()
            with col3:
                if st.button("Predice el precio de Santander mañana"):
                    st.session_state.prompt_from_button = "Predice el precio de Santander para mañana"
                    st.rerun()

    # --- 5. LÓGICA DEL CHAT ---

    # Mostrar el historial de mensajes existente
    for mensaje in st.session_state.historial_display:
        with st.chat_message(mensaje["role"]):
            st.markdown(mensaje["content"])

    # Capturar la entrada del usuario (del input de chat o de los botones de ejemplo)
    prompt = st.chat_input("Escribe tu consulta financiera...") or st.session_state.pop("prompt_from_button", None)

    if prompt:
        # Mostrar el mensaje del usuario inmediatamente
        st.chat_message("user").markdown(prompt)
        st.session_state.historial_display.append({"role": "user", "content": prompt})

        # Preparar y llamar al grafo de LangChain
        try:
            current_date_str = datetime.now().strftime("%Y-%m-%d")
            initial_state = {
                "input": prompt,
                "historial_preguntas": st.session_state.historial_preguntas_llm,
                "historial_completo": st.session_state.historial_completo_grafo,
                "fecha_actual": current_date_str,
                # El resto de claves se llenarán dentro del grafo
            }

            # Mostrar un mensaje de "pensando..." mientras se procesa
            with st.chat_message("assistant"):
                with st.spinner("Procesando tu consulta..."):
                    result = graph.invoke(initial_state)

                # Extraer la respuesta y la fuente del resultado
                respuesta = result.get("respuesta", "Lo siento, no pude generar una respuesta.")
                fuente = result.get("fuente", "desconocida")
                
                # Simular efecto de "escribir" para una mejor UX
                response_placeholder = st.empty()
                full_response = ""
                for chunk in respuesta.split():
                    full_response += chunk + " "
                    time.sleep(0.03)
                    response_placeholder.markdown(full_response + "▌")
                response_placeholder.markdown(full_response)
                
                # Mostrar la fuente y otros elementos debajo de la respuesta
                st.caption(f"Fuente de datos: {fuente}")

                # Mostrar gráfico si está disponible
                if fuente == "series_temporales" and result.get("grafico_base64"):
                    st.image("data:image/png;base64," + result["grafico_base64"], caption="📈 Gráfico de evolución")

                # Mostrar fragmentos si es una respuesta RAG
                if fuente == "qdrant" and result.get("fragmentos"):
                    with st.expander("🔍 Ver fragmentos de documentos utilizados"):
                        for i, frag in enumerate(result["fragmentos"]):
                            display_frag = frag[:350] + "..." if len(frag) > 350 else frag
                            st.info(f"**Fragmento {i+1}:**\n\n> {display_frag}")
            
            # --- Actualizar historiales en st.session_state ---
            # Para el display, guardamos todo el contenido formateado
            full_assistant_content = f"{respuesta}\n\n*Fuente de datos: {fuente}*"
            st.session_state.historial_display.append({"role": "assistant", "content": full_assistant_content})
            
            # Para el LLM, solo las preguntas del usuario
            st.session_state.historial_preguntas_llm.append(prompt)
            st.session_state.historial_preguntas_llm = st.session_state.historial_preguntas_llm[-3:]

            # Para el grafo, el historial completo que él mismo gestiona
            st.session_state.historial_completo_grafo = result.get("historial_completo", [])

        except Exception as e:
            error_msg = f"⚠️ Ocurrió un error inesperado al procesar tu consulta: {e}"
            st.chat_message("assistant").error(error_msg)
            st.session_state.historial_display.append({"role": "assistant", "content": error_msg})

if __name__ == "__main__":
    main()