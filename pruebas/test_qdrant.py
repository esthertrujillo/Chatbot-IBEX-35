import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from collections import Counter

# Cargar variables de entorno
load_dotenv()

# Conexión al cliente Qdrant
client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
    timeout=60.0
)

# Leer puntos con payload
coleccion = "resumenes_ibex35"
print(f"📡 Explorando colección '{coleccion}'...\n")

result = client.scroll(
    collection_name=coleccion,
    with_payload=True,
    limit=1000  # puedes aumentar si tienes más puntos
)

puntos = result[0]
print(f"✅ Puntos encontrados: {len(puntos)}")

# Contar empresas en el payload
empresas = [p.payload.get("empresa", "desconocida") for p in puntos]
conteo_empresas = Counter(empresas)

print("\n📊 Empresas presentes en el índice:")
for empresa, count in conteo_empresas.most_common():
    print(f"- {empresa}: {count} fragmentos")

# Buscar fragmentos de Santander
print("\n🔍 Buscando fragmentos que mencionen 'Santander':")
encontrados = 0
for p in puntos:
    resumen = p.payload.get("resumen", "").lower()
    if "santander" in resumen:
        print("\n📝 Fragmento encontrado:")
        print(p.payload.get("resumen", "")[:10000], "...")  # Muestra primeros 1000 caracteres
        encontrados += 1

if encontrados == 0:
    print("⚠️ No se encontraron fragmentos que contengan 'Santander'.")

print("\n✅ Fin del análisis.")
