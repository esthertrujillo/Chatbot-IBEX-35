import torch
# This is often needed to prevent issues with PyTorch dependencies in certain environments
# It should be placed at the very top to be effective before any other torch-related operations.
torch.classes = None 

import streamlit as st
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage # Import for chat history conversion

# Import the compiled graph and the ChatbotState TypedDict from your main.py
# Make sure your main.py is accessible and `build_graph()` is defined there.
# If your graph is named 'main_graph.py' and exports 'graph' directly, adjust the import below:
# from main_graph import graph
# Otherwise, if main.py defines build_graph() and you want to compile it here:
from main_graph import build_graph, ChatbotState

# Compile the graph (if not already compiled and directly imported)
graph = build_graph()


# --- Streamlit Page Configuration ---
st.set_page_config(page_title="Chatbot Financiero IBEX 35", page_icon="💬")
st.title("🤖 Chatbot Financiero IBEX 35")
st.markdown("Consulta precios históricos de acciones del IBEX 35 o analiza documentos financieros usando lenguaje natural.")

# --- Initialize Chat History in Streamlit Session State ---
# 'messages' will store all interactions (user and assistant) for display
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Initial welcome message from the assistant to start the conversation
    st.session_state.messages.append({"role": "assistant", "content": "¡Hola! Estoy listo para ayudarte con consultas sobre el IBEX 35. ¿Sobre qué empresa te gustaría saber?"})

# --- Display Chat History ---
# Renders all messages stored in session_state
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        # Display the main content of the message
        st.markdown(message["content"])
        
        # Logic to display additional elements like graphs or RAG fragments
        # These are saved in 'full_response_data' for assistant messages
        if message["role"] == "assistant" and "full_response_data" in message:
            full_data = message["full_response_data"]
            
            # Show graph if it's a time series response
            if full_data.get("fuente") == "series_temporales" and full_data.get("grafico_base64"):
                st.image("data:image/png;base64," + full_data["grafico_base64"], caption="Predicción de Series Temporales")
            
            # Show fragments used if it's a Qdrant RAG response
            if full_data.get("fuente") == "qdrant" and full_data.get("fragmentos"):
                with st.expander("🔍 Fragmentos usados (RAG)"):
                    for i, frag in enumerate(full_data["fragmentos"]):
                        st.markdown(f"**Fragmento {i+1}:**\n{frag}")

# --- User Input and Chatbot Logic ---
# st.chat_input appears at the bottom and sends input on Enter key press
if prompt := st.chat_input("Escribe tu pregunta aquí..."):
    # Add the user's question to the history before processing it
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Render the user's message immediately in the chat
    with st.chat_message("user"):
        st.markdown(prompt)

    # Show a spinner while the chatbot is processing
    with st.spinner("El chatbot está pensando..."):
        try:
            # Convert Streamlit chat history to LangChain BaseMessage format for the graph
            langchain_chat_history: list[BaseMessage] = []
            for msg in st.session_state.messages:
                if msg["role"] == "user":
                    langchain_chat_history.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    # For assistant messages, we only care about the 'content' for history
                    langchain_chat_history.append(AIMessage(content=msg["content"]))
            
            # Prepare the initial state for the graph invocation
            # Ensure all fields of the ChatbotState TypedDict are present
            initial_state: ChatbotState = {
                "input": prompt,
                "chat_history": langchain_chat_history, # Pass the converted history
                "empresa": None,
                "tipo_pregunta": None,
                "respuesta": None,
                "fuente": None,
                "fecha_inicio": None,
                "fecha_fin": None,
                "grafico_base64": None,
                "categoria_inicial": None
            }

            # Invoke the graph with the user's question and history
            result: ChatbotState = graph.invoke(initial_state)
            
            # Extract main response and source from the result
            respuesta = result.get("respuesta", "Lo siento, no pude generar una respuesta.")
            fuente = result.get("fuente", "desconocida")

            # Check for early exit messages (greetings, out-of-scope) from the initial filter
            if result.get("categoria_inicial") in ["saludo", "fuera_de_alcance"] and respuesta is not None:
                assistant_content_text = respuesta # Use the direct response from the filter
            else:
                assistant_content_text = f"**Bot (Fuente: {fuente})**: {respuesta}"
            
            # Add the complete response (text + additional data) to the session state history
            st.session_state.messages.append({
                "role": "assistant",
                "content": assistant_content_text, # Main text content
                "full_response_data": result # Save the full result object for display of graphs/fragments
            })
            
            # Render the assistant's response immediately
            with st.chat_message("assistant"):
                st.markdown(assistant_content_text) # Display the main text

                # Display graph if applicable (re-check here for immediate rendering)
                if fuente == "series_temporales" and result.get("grafico_base64"):
                    st.image("data:image/png;base64," + result["grafico_base64"], caption="Predicción de Series Temporales")

                # Display fragments used if it was Qdrant/RAG (re-check here for immediate rendering)
                if fuente == "qdrant" and result.get("fragmentos"):
                    with st.expander("🔍 Fragmentos usados (RAG)"):
                        for i, frag in enumerate(result["fragmentos"]):
                            st.markdown(f"**Fragmento {i+1}:**\n{frag}")

        except Exception as e:
            # Error handling: display message and add to history
            error_message = f"⚠️ Ocurrió un error al procesar tu consulta: {e}"
            st.error(error_message) # Display the error in red
            st.session_state.messages.append({"role": "assistant", "content": error_message})
            with st.chat_message("assistant"):
                st.markdown(error_message)
