# app.py

from main_graph import build_graph

def main():
    print("🤖 Chatbot Financiero IBEX 35 (Groq + LangGraph)\n")
    print("Escribe una pregunta relacionada con cotizaciones, informes financieros o precios actuales.")
    print("Escribe 'salir' para terminar.\n")

    # Cargamos el grafo
    grafo = build_graph()

    while True:
        try:
            pregunta = input("🧑 Tú: ").strip()
            if not pregunta:
                print("⚠️ Por favor, escribe una pregunta.")
                continue

            if pregunta.lower() in ["salir", "exit", "quit"]:
                print("👋 Hasta la próxima.")
                break

            # Ejecutar el flujo LangGraph
            result = grafo.invoke({"input": pregunta})
            print(f"🤖 Bot ({result.get('fuente', 'desconocido')}): {result.get('respuesta', 'Sin respuesta generada.')}\n")

        except KeyboardInterrupt:
            print("\n👋 Interrumpido por el usuario. Hasta pronto.")
            break
        except Exception as e:
            print("⚠️ Error procesando la consulta:", str(e))

if __name__ == "__main__":
    main()
