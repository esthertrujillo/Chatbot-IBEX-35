from qdrant_utils import buscar_en_qdrant

consulta = "¿Qué dice BBVA sobre sostenibilidad en 2023?"
resultados = buscar_en_qdrant(consulta)

for r in resultados:
    print(r.payload.get("fragmento", ""))
