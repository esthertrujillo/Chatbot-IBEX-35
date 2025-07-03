import streamlit as st
from main_graph import graph
from datetime import datetime
import time
import json

def main():
    """
    Función principal que renderiza la aplicación de chatbot en Streamlit.
    """
    # --- 1. CONFIGURACIÓN DE LA PÁGINA ---
    st.set_page_config(page_title="Chatbot Financiero IBEX 35", page_icon="📈", layout="wide")

    # --- Inicializar los historiales en st.session_state si no existen ---
    if "historial_display" not in st.session_state:
        st.session_state.historial_display = []
    if "historial_preguntas" not in st.session_state:
        st.session_state.historial_preguntas = []
    if "historial_completo" not in st.session_state:
        st.session_state.historial_completo = []
    # También inicializa prompt_from_button si no existe para evitar KeyError on first run
    if "prompt_from_button" not in st.session_state:
        st.session_state.prompt_from_button = None

    if "datos_empresa_cache" not in st.session_state:
        st.session_state.datos_empresa_cache = {}

    # --- 2. BARRA LATERAL ---
    with st.sidebar:
        st.title("ℹ️ Acerca del Chatbot")
        st.info(
            "Este chatbot te permite interactuar con datos del IBEX 35. "
            "Puedes pedir precios históricos, análisis de documentos (RAG), predicciones futuras, "
        )

        st.warning(
            "**Aviso:** Este es un chatbot experimental. "
            "La información proporcionada no constituye asesoramiento financiero."
        )

        st.divider()

        # Botón para limpiar el historial del chat
        if st.button("🗑️ Limpiar Historial del Chat"):
            st.session_state.historial_display = []
            st.session_state.historial_preguntas = []
            st.session_state.historial_completo = []
            st.session_state.datos_empresa_cache = {} # Clear cache too
            st.rerun()

    # --- 3. INTERFAZ PRINCIPAL ---

    col1, col2, col3 = st.columns([2.5, 1, 2.5])
    with col2:
        st.image("utils/png.jpg")

    st.title("Chatbot Financiero del IBEX 35")
    st.caption("Consulta precios, analiza documentos o pide predicciones  del mercado español.")

    # --- 4. MENSAJE DE BIENVENIDA Y EJEMPLOS (si el chat está vacío) ---
    # Now this check is safe because historial_display is guaranteed to exist
    if not st.session_state.historial_display:
        with st.container(border=True, height=200):
            st.write("👋 **¡Hola! ¿En qué puedo ayudarte hoy?**")
            st.write("Puedes probar con alguna de estas opciones:")

            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Dame el precio de BBVA ayer"):
                    st.session_state.prompt_from_button = "Dame el precio de BBVA ayer"
                    st.rerun()
            with col2:
                if st.button("¿Qué beneficio neto atribuido obtuvo Iberdrola en 2024?"):
                    st.session_state.prompt_from_button = "¿Qué beneficio neto atribuido obtuvo Iberdrola en 2024?"
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
    # The pop operation is fine here as prompt_from_button is now initialized
    prompt = st.chat_input("Escribe tu consulta financiera...") or st.session_state.pop("prompt_from_button", None)

    if prompt:
        st.chat_message("user").markdown(prompt)
        st.session_state.historial_display.append({"role": "user", "content": prompt})

        try:
            current_date_str = datetime.now().strftime("%Y-%m-%d")
            # The initial_state for the graph should also include the datos_empresa_cache
            initial_state = {
                "input": prompt,
                "historial_preguntas": st.session_state.historial_preguntas,
                "historial_completo": st.session_state.historial_completo,
                "fecha_actual": current_date_str,
                "empresa": None,
                "tipo_pregunta": None,
                "respuesta": None,
                "fuente": None,
                "fecha_inicio": None,
                "fecha_fin": None,
                "grafico_base64": None,
                "datos_recopilados": None,
                "datos_empresa_cache": st.session_state.datos_empresa_cache # Pass the cache from session state
            }

            with st.chat_message("assistant"):
                with st.spinner("Procesando tu consulta..."):
                    result = graph.invoke(initial_state)

                respuesta = result.get("respuesta", "Lo siento, no pude generar una respuesta.")
                fuente = result.get("fuente", "desconocida")

                response_placeholder = st.empty()
                full_response = ""
                for chunk in respuesta.split():
                    full_response += chunk + " "
                    time.sleep(0.03)
                    response_placeholder.markdown(full_response + "▌")
                response_placeholder.markdown(full_response)

                st.caption(f"Fuente de datos: {fuente}")

                if result.get("grafico_base64"):
                    st.image("data:image/png;base64," + result["grafico_base64"], caption="📈 Gráfico de evolución")

                if fuente == "qdrant" and result.get("fragmentos"):
                    with st.expander("🔍 Ver fragmentos de documentos utilizados"):
                        for i, frag in enumerate(result["fragmentos"]):
                            display_frag = frag[:350] + "..." if len(frag) > 350 else frag
                            st.info(f"**Fragmento {i+1}:**\n\n> {display_frag}")

                if result.get("datos_recopilados"):
                    with st.expander("📊 Datos recopilados para la comparación (DEBUG)"):
                        st.json(result["datos_recopilados"])

            full_assistant_content = f"{respuesta}\n\n*Fuente de datos: {fuente}*"
            st.session_state.historial_display.append({"role": "assistant", "content": full_assistant_content})

            st.session_state.historial_preguntas = result.get("historial_preguntas", [])
            st.session_state.historial_completo = result.get("historial_completo", [])
            st.session_state.datos_empresa_cache = result.get("datos_empresa_cache", {}) # Update cache from graph result

        except Exception as e:
            error_msg = f"⚠️ Ocurrió un error inesperado al procesar tu consulta: {e}"
            st.chat_message("assistant").error(error_msg)
            st.session_state.historial_display.append({"role": "assistant", "content": error_msg})
            # Consider more robust error handling for session state here if needed,
            # but usually resetting them is good for a fresh start after an error.
            st.session_state.historial_preguntas = []
            st.session_state.historial_completo = []
            st.session_state.datos_empresa_cache = {}


if __name__ == "__main__":
    main()