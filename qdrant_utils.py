from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
import uuid
import os
from dotenv import load_dotenv
import torch
torch.classes = None

# Cargar las variables del archivo .env
load_dotenv()

# Conexión al servidor Qdrant
qdrant_client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
    timeout=60.0
)

modelo = SentenceTransformer("infloat/e5-large-v2")
coleccion = "resumenes_ibex35"

# Función: Vectorizar un texto
def vectorizar_texto(texto):
    """
    Genera el embedding del texto usando el modelo SentenceTransformer.
    """
    return modelo.encode(texto).tolist()

# Función: Buscar en Qdrant
def buscar_en_qdrant(consulta, n_resultados=5):
    """
    Busca los fragmentos más relevantes en la colección de Qdrant.
    """
    vector = vectorizar_texto(consulta)
    resultados = qdrant_client.search(
        collection_name=coleccion,
        query_vector=vector,
        limit=n_resultados,
        with_payload=True
    )
    return resultados

# Función: Indexar fragmentos nuevos
def indexar_fragmentos(fragmentos):
    """
    Inserta nuevos fragmentos en la colección de Qdrant.
    Cada fragmento se almacena como un punto con un id UUID y su vector.
    """
    puntos = []
    for fragmento in fragmentos:
        puntos.append({
            "id": str(uuid.uuid4()),
            "vector": vectorizar_texto(fragmento),
            "payload": {"fragmento": fragmento}
        })
    qdrant_client.upsert(
        collection_name=coleccion,
        points=puntos
    )
    return f"{len(puntos)} fragmentos indexados en {coleccion}."
