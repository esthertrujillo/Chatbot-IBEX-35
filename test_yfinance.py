from dotenv import load_dotenv
import os

# Cargar las variables de entorno
load_dotenv()

# Leer la API key
groq_api_key = os.getenv("GROQ_API_KEY")

# Para depuración temporal (⚠ NO dejar en producción)
print(f"🔑 GROQ_API_KEY cargada: {groq_api_key}")

from dotenv import load_dotenv
import os

# Cargar las variables de entorno
load_dotenv()

# Leer la API key
groq_api_key = os.getenv("GROQ_API_KEY")

# Para depuración temporal (⚠ NO dejar en producción)
print(f"🔑 GROQ_API_KEY cargada: {groq_api_key}")

from groq import Groq

client = Groq(api_key=groq_api_key)

# Test directo
response = client.chat.completions.create(
    model="llama3-70b-8192",  # modelo activo
    messages=[{"role": "user", "content": "Dime hola"}]
)

print(response.choices[0].message.content)
