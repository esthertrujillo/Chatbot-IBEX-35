import streamlit as st
# Asegúrate de que tu archivo main_graph.py (o main.py) contenga la variable 'graph' compilada
from main_graph import graph 
from datetime import datetime
import time # Importado para el efecto de "escribiendo"
import json # Necesario para pretty-print JSON

def main():
    """
    Función principal que renderiza la aplicación de chatbot en Streamlit.
    """
    # --- 1. CONFIGURACIÓN DE LA PÁGINA ---
    st.set_page_config(page_title="Chatbot Financiero IBEX 35", page_icon="📈", layout="wide")

    # --- 2. BARRA LATERAL (SIDEBAR) ---
    with st.sidebar:
        st.title("ℹ️ Acerca del Chatbot")
        st.info(
            "Este chatbot te permite interactuar con datos del IBEX 35. "
            "Puedes pedir precios históricos, análisis de documentos (RAG), predicciones futuras, "
            "o **comparaciones entre empresas**."
        )

        st.warning(
            "**Aviso:** Este es un chatbot experimental. "
            "La información proporcionada no constituye asesoramiento financiero."
        )

        st.divider()

        # Botón para limpiar el historial del chat
        if st.button("🗑️ Limpiar Historial del Chat"):
            # Limpiamos todas las variables de estado de la sesión relevantes
            st.session_state.historial_display = []
            st.session_state.historial_preguntas = [] # Corregido para que coincida con el nombre del estado del grafo
            st.session_state.historial_completo = []  # Corregido para que coincida con el nombre del estado del grafo
            st.rerun()

    # --- 3. INTERFAZ PRINCIPAL ---

    col1, col2, col3 = st.columns([2.5, 1, 2.5])
    with col2:
        st.image("utils/png.jpg") 

    st.title("Chatbot Financiero del IBEX 35")
    st.caption("Consulta precios, analiza documentos, pide predicciones o **compara empresas** del mercado español.")

    # Inicializar los historiales en st.session_state si no existen
    # Nombres de las claves actualizados para coincidir con ChatbotState en main_graph
    if "historial_display" not in st.session_state:
        st.session_state.historial_display = []
    if "historial_preguntas" not in st.session_state: # Ahora coincide con el estado del grafo
        st.session_state.historial_preguntas = []
    if "historial_completo" not in st.session_state: # Ahora coincide con el estado del grafo
        st.session_state.historial_completo = []

    # --- 4. MENSAJE DE BIENVENIDA Y EJEMPLOS (si el chat está vacío) ---
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
            # El estado inicial debe coincidir con la TypedDict ChatbotState en main_graph
            initial_state = {
                "input": prompt,
                "historial_preguntas": st.session_state.historial_preguntas, # Usamos el historial gestionado en Streamlit
                "historial_completo": st.session_state.historial_completo, # Usamos el historial gestionado en Streamlit
                "fecha_actual": current_date_str,
                "empresa": None, # Inicializa todas las claves de ChatbotState
                "tipo_pregunta": None,
                "respuesta": None,
                "fuente": None,
                "fecha_inicio": None,
                "fecha_fin": None,
                "grafico_base64": None,
                "datos_recopilados": None # Inicializa el nuevo campo
            }

            # Mostrar un mensaje de "pensando..." mientras se procesa
            with st.chat_message("assistant"):
                with st.spinner("Procesando tu consulta..."):
                    # El grafo ahora maneja el historial_completo y historial_preguntas y los devuelve actualizados
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
                if result.get("grafico_base64"): # No es necesario chequear 'fuente' aquí, si existe, se muestra
                    st.image("data:image/png;base64," + result["grafico_base64"], caption="📈 Gráfico de evolución")

                # Mostrar fragmentos si es una respuesta RAG
                if fuente == "qdrant" and result.get("fragmentos"):
                    with st.expander("🔍 Ver fragmentos de documentos utilizados"):
                        for i, frag in enumerate(result["fragmentos"]):
                            display_frag = frag[:350] + "..." if len(frag) > 350 else frag
                            st.info(f"**Fragmento {i+1}:**\n\n> {display_frag}")
                
                # Opcional: Mostrar datos recopilados para depuración en el nodo de comparación
                if fuente == "comparacion" and result.get("datos_recopilados"):
                    with st.expander("📊 Datos recopilados para la comparación (DEBUG)"):
                        st.json(result["datos_recopilados"])
            
            # --- Actualizar historiales en st.session_state ---
            # Para el display, guardamos todo el contenido formateado
            full_assistant_content = f"{respuesta}\n\n*Fuente de datos: {fuente}*"
            st.session_state.historial_display.append({"role": "assistant", "content": full_assistant_content})
            
            # El grafo gestiona y devuelve los historiales actualizados en 'result'
            st.session_state.historial_preguntas = result.get("historial_preguntas", [])
            st.session_state.historial_completo = result.get("historial_completo", [])

        except Exception as e:
            error_msg = f"⚠️ Ocurrió un error inesperado al procesar tu consulta: {e}"
            st.chat_message("assistant").error(error_msg)
            st.session_state.historial_display.append({"role": "assistant", "content": error_msg})
            # En caso de error, podríamos limpiar los historiales para evitar estados corruptos
            st.session_state.historial_preguntas = []
            st.session_state.historial_completo = []


if __name__ == "__main__":
    main()