from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
import uuid
import os
from dotenv import load_dotenv
import torch
torch.classes = None  # Prevención para ciertos errores en Windows

# Cargar variables del entorno
load_dotenv()

# Conexión a Qdrant
client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
    timeout=60.0
)

modelo = SentenceTransformer("intfloat/e5-large-v2")
coleccion = "resumenes_ibex35"

# Función: Vectorizar texto
def vectorizar_texto(texto):
    return modelo.encode(texto).tolist()

# Función: Buscar en Qdrant
def buscar_en_qdrant(consulta, n_resultados=5):
    vector = vectorizar_texto(consulta)
    resultados = client.search(
        collection_name=coleccion,
        query_vector=vector,
        limit=n_resultados,
        with_payload=True
    )
    return resultados

# Función: Indexar fragmentos nuevos (usa "resumen" como clave real del payload)
def indexar_fragmentos(fragmentos, empresa="desconocida", archivo="manual"):
    puntos = []
    for resumen in fragmentos:
        puntos.append({
            "id": str(uuid.uuid4()),
            "vector": vectorizar_texto(resumen),
            "payload": {
                "resumen": resumen,
                "empresa": empresa,
                "archivo": archivo
            }
        })
    client.upsert(
        collection_name=coleccion,
        points=puntos
    )
    return f"{len(puntos)} fragmentos indexados correctamente en {coleccion}."
