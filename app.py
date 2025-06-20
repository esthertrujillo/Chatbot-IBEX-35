import streamlit as st
from main_graph import graph
import torch
torch.classes = None  # Para evitar problemas con dependencias si usas Groq + LangChain

st.set_page_config(page_title="Chatbot IBEX 35", page_icon="💬")
st.title("🤖 Chatbot Financiero IBEX 35")
st.markdown("Consulta precios históricos de acciones del IBEX 35 o analiza documentos financieros usando lenguaje natural.")

# Inicializar el historial de la conversación
if "historial" not in st.session_state:
    st.session_state.historial = []

# Entrada del usuario
pregunta = st.text_input("🧑 Tú:", placeholder="Ej: ¿Cuál es la cotización de mañana de BBVA?")

if st.button("Enviar") and pregunta:
    try:
        result = graph.invoke({"input": pregunta})
        respuesta = result.get("respuesta", "Sin respuesta generada.")
        fuente = result.get("fuente", "desconocida")

        # Añadir al historial
        st.session_state.historial.append(("Tú", pregunta))
        st.session_state.historial.append((f"Bot (Fuente: {fuente})", respuesta))

        # Mostrar la respuesta principal
        st.markdown(f"**Bot (Fuente: {fuente})**")
        st.markdown(respuesta)

        # Mostrar gráfico si aplica
        if fuente == "series_temporales" and result.get("grafico_base64"):
            st.image("data:image/png;base64," + result["grafico_base64"])

        # Mostrar fragmentos usados si fue Qdrant/RAG
        if fuente == "qdrant" and result.get("fragmentos"):
            with st.expander("🔍 Fragmentos usados (RAG)"):
                for frag in result["fragmentos"]:
                    st.markdown(f"- {frag}")

    except Exception as e:
        st.error(f"⚠️ Error procesando la consulta: {e}")

# Mostrar el historial completo
if st.session_state.historial:
    st.markdown("## 📝 Historial de la conversación")
    for autor, texto in st.session_state.historial:
        st.markdown(f"**{autor}:** {texto}")
