# app_streamlit.py

import streamlit as st
from main_graph import build_graph

st.set_page_config(page_title="Chatbot IBEX 35", page_icon="💬")
st.title("🤖 Chatbot Financiero IBEX 35")
st.markdown("Consulta precios históricos de acciones del IBEX 35 usando lenguaje natural.")

# Construir el grafo una sola vez (no cada vez que se renderiza la página)
@st.cache_resource
def cargar_grafo():
    return build_graph()

grafo = cargar_grafo()

# Inicializar el estado de conversación
if "historial" not in st.session_state:
    st.session_state.historial = []

# Entrada de usuario
pregunta = st.text_input("🧑 Tú:", placeholder="Ej: ¿Cuál fue el precio medio de Iberdrola en marzo de 2023?")

if st.button("Enviar") and pregunta:
    try:
        result = grafo.invoke({"input": pregunta})
        respuesta = result.get("respuesta", "Sin respuesta.")
        fuente = result.get("fuente", "desconocida")

        st.session_state.historial.append(("Tú", pregunta))
        st.session_state.historial.append((f"Bot ({fuente})", respuesta))

        # Mostrar imagen si hay gráfico de series temporales
        if fuente == "series_temporales" and result.get("grafico_base64"):
            st.image("data:image/png;base64," + result["grafico_base64"])

    except Exception as e:
        st.error(f"⚠️ Error procesando la consulta: {e}")

# Mostrar historial en orden inverso (últimos primero)
for autor, texto in reversed(st.session_state.historial):
    st.markdown(f"**{autor}:** {texto}")
