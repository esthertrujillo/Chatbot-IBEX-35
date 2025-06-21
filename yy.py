import os
import sys
from main_graph import graph # Asumiendo que 'main_graph.py' es tu 'main.py' con el grafo compilado.

# Ajusta la ruta si es necesario para que Python encuentre main_graph
# Si main_graph.py está en el mismo directorio, no necesitas esto.
# Si está en un subdirectorio, por ejemplo 'src/', podrías necesitar:
# sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))


def run_terminal_chat():
    """
    Ejecuta un chatbot interactivo en la terminal.
    """
    print("🤖 Chatbot Financiero IBEX 35")
    print("Consulta precios históricos de acciones del IBEX 35 o analiza documentos financieros usando lenguaje natural.")
    print("Escribe 'salir' o 'exit' para terminar la conversación.")
    print("-" * 50)

    while True:
        pregunta = input("\n🧑 Tú: ")

        if pregunta.lower() in ["salir", "exit"]:
            print("👋 ¡Hasta luego!")
            break

        try:
            # Invocar el grafo con la pregunta del usuario
            result = graph.invoke({"input": pregunta})

            # Extraer la respuesta y la fuente
            respuesta = result.get("respuesta", "Sin respuesta generada.")
            fuente = result.get("fuente", "desconocida")

            print(f"\n**Bot (Fuente: {fuente})**")
            print(respuesta)

            # Mostrar fragmentos si la fuente es Qdrant
            if fuente == "qdrant" and result.get("fragmentos"):
                print("\n🔍 Fragmentos usados (RAG):")
                for i, frag in enumerate(result["fragmentos"]):
                    print(f"- Fragmento {i+1}: {frag.strip()}") # .strip() para limpiar posibles saltos de línea extra

            # Nota: Los gráficos Base64 no se pueden mostrar directamente en la terminal.
            # Puedes optar por guardarlos en un archivo si el nodo 'series_temporales'
            # te devuelve el base64. Si no, esta parte es omitida en la terminal.
            # if fuente == "series_temporales" and result.get("grafico_base64"):
            #     print("\n[!] Se generó un gráfico, pero no se puede mostrar en la terminal.")
            #     # Opcional: guardar el gráfico en un archivo
            #     # import base64
            #     # try:
            #     #     with open("grafico_generado.png", "wb") as fh:
            #     #         fh.write(base66.b64decode(result["grafico_base64"]))
            #     #     print("Gráfico guardado como 'grafico_generado.png'")
            #     # except Exception as e:
            #     #     print(f"Error al guardar el gráfico: {e}")

        except Exception as e:
            print(f"⚠️ Error procesando la consulta: {e}")

# Asegúrate de que el script se ejecute solo cuando es llamado directamente
if __name__ == "__main__":
    run_terminal_chat()