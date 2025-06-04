import streamlit as st
from datetime import datetime
from main_graph import build_graph

# --------------------------------------------------
# Configuración general de la página
# --------------------------------------------------
st.set_page_config(page_title="Chatbot IBEX 35", page_icon="📈", layout="centered")

st.markdown("""
<style>
.chat-bubble-user {
    background-color: #d0e6ff;
    border-radius: 15px;
    padding: 10px;
    margin: 5px 0;
    text-align: right;
}
.chat-bubble-bot {
    background-color: #f0f2f6;
    border-radius: 15px;
    padding: 10px;
    margin: 5px 0;
    text-align: left;
}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# Encabezado
# --------------------------------------------------
st.title("🤖 Chatbot Financiero IBEX 35")
st.markdown("Consulta con lenguaje natural el precio medio de acciones del IBEX 35 y más datos financieros relevantes.")

st.divider()

# --------------------------------------------------
# Inicialización del estado
# --------------------------------------------------
@st.cache_resource
def cargar_grafo():
    return build_graph()

grafo = cargar_grafo()

if "historial" not in st.session_state:
    st.session_state.historial = []

# --------------------------------------------------
# Entrada del usuario
# --------------------------------------------------
with st.form("chat_form"):
    pregunta = st.text_input("Haz tu pregunta:", placeholder="Ej: ¿Cuál fue el precio medio de Iberdrola en marzo de 2023?")
    enviar = st.form_submit_button("📤 Enviar")

if enviar and pregunta:
    try:
        result = grafo.invoke({"input": pregunta})
        respuesta = result.get("respuesta", "Sin respuesta.")
        fuente = result.get("fuente", "desconocida")

        # Añadir al historial
        st.session_state.historial.append(("Tú", pregunta, "user"))
        st.session_state.historial.append((f"Bot ({fuente})", respuesta, "bot"))
    except Exception as e:
        st.error(f"⚠️ Error procesando la consulta: {e}")

# --------------------------------------------------
# Mostrar conversación
# --------------------------------------------------
st.subheader("📜 Conversación")
for autor, texto, rol in st.session_state.historial:
    if rol == "user":
        st.markdown(f"<div class='chat-bubble-user'><strong>{autor}:</strong><br>{texto}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='chat-bubble-bot'><strong>{autor}:</strong><br>{texto}</div>", unsafe_allow_html=True)
