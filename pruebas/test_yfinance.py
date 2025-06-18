from main_graph import graph  # importa tu grafo de LangGraph

if __name__ == "__main__":
    while True:
        user_input = input("📝 Escribe tu pregunta financiera (o 'salir'): ")
        if user_input.lower() == "salir":
            break

        state = {"input": user_input}
        print("🚀 Ejecutando el flujo LangGraph...")
        final_state = graph.invoke(state)

        print("📤 Respuesta final:")
        print(final_state.get("respuesta", "No se generó respuesta"))
        print("📄 Fuente:", final_state.get("fuente", "desconocida"))
        print("🔍 Tipo:", final_state.get("tipo_pregunta", "no detectado"))
        print("------\n")


#pruebas
#¿Cuál fue el precio medio de Endesa entre enero y marzo de 2023?

