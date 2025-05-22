# app.py

from main_graph import build_graph

def main():
    print("🤖 Chatbot Financiero IBEX 35 (Groq + LangGraph)\n")
    print("Escribe una pregunta relacionada con cotizaciones, informes financieros o precios actuales.")
    print("Escribe 'salir' para terminar.\n")

    # Cargamos el grafo
    grafo = build_graph()

    while True:
        pregunta = input("🧑 Tú: ")
        if pregunta.lower() in ["salir", "exit", "quit"]:
            print("👋 Hasta la próxima.")
            break

        try:
            # Ejecutar el flujo LangGraph
            result = grafo.invoke({"input": pregunta})
            print(f"🤖 Bot ({result['fuente']}): {result['respuesta']}\n")
        except Exception as e:
            print("⚠️ Error procesando la consulta:", str(e))

if __name__ == "__main__":
    main()
