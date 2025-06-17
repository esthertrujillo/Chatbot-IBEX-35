import streamlit as st
from main_graph import build_graph
import torch
torch.classes = None


st.set_page_config(page_title="Chatbot IBEX 35", page_icon="💬")
st.title("🤖 Chatbot Financiero IBEX 35")
st.markdown("Consulta precios históricos de acciones del IBEX 35 o analiza documentos financieros usando lenguaje natural.")

# Cargar el grafo LangGraph
grafo = build_graph()

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

        # Añadir al historial
        st.session_state.historial.append(("Tú", pregunta))
        st.session_state.historial.append((f"Bot (Fuente: {fuente})", respuesta))

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

# Mostrar historial
for autor, texto in st.session_state.historial:
    st.markdown(f"**{autor}:** {texto}")
