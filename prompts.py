from datetime import date
HOY = date.today().strftime("%Y-%m-%d")



PROMPT_SERIES = """
Actúa como un analista financiero experto en series temporales de acciones del IBEX 35.

Tu tarea es responder a la siguiente pregunta relacionada con el comportamiento histórico de una acción.

Pregunta del usuario:
{pregunta}

Devuelve tu respuesta en formato JSON con la clave "respuesta", por ejemplo:
{
  "respuesta": "La acción de Iberdrola ha tenido una tendencia alcista en el último año, con un incremento acumulado del 8%. La volatilidad se ha mantenido estable respecto al año anterior."
}
"""

PROMPT_DOCUMENTOS = """
Eres un asistente especializado en interpretar información contenida en informes anuales, presentaciones de resultados y memorias corporativas de empresas del IBEX 35.

Tu tarea es responder la siguiente pregunta como si accedieras a dichos documentos, incluso si estás simulando.

Pregunta del usuario:
{pregunta}

Devuelve la respuesta en formato JSON con la clave "respuesta", por ejemplo:
{
  "respuesta": "Según el informe anual 2023, Telefónica incrementó su beneficio neto un 15% respecto al año anterior, destacando el crecimiento en Brasil y Alemania."
}
"""

PROMPT_API = """
Eres un sistema que accede a información financiera en tiempo real a través de una API.

Dado que esta es una simulación, responde como si hubieras consultado una API externa que ofrece precios actuales de acciones.

Pregunta del usuario:
{pregunta}

Devuelve la respuesta en formato JSON con la clave "respuesta", por ejemplo:
{
  "respuesta": "El precio actual de las acciones de Banco Santander es 3,92€, con una variación diaria de +0,85%."
}
"""
PROMPT_API_EXTRAER = """
Extrae los siguientes datos de la pregunta sobre precios de acciones del IBEX 35:

- empresa (en minúsculas)
- fecha_inicio (YYYY-MM-DD)
- fecha_fin (YYYY-MM-DD)

Si no se menciona el año explícitamente, **asume que se refiere al año 2025**.

🟢 Consejo adicional:
Si la pregunta contiene expresiones como "hoy", "ayer" o "última semana", utiliza la fecha actual `{hoy}` como referencia y ajusta las fechas:

- "hoy" → fecha_inicio = fecha_fin = {hoy}
- "ayer" → fecha_inicio = fecha_fin = {ayer}
- "última semana" → fecha_inicio = {hoy_menos_7}, fecha_fin = {hoy}

---
Responde **EXCLUSIVAMENTE** en formato JSON, sin explicaciones, texto adicional o puntuación extra.
La respuesta debe ser **SOLAMENTE** el objeto JSON.

Ejemplo de formato de respuesta:
{{
  "empresa": "iberdrola",
  "fecha_inicio": "2023-03-01",
  "fecha_fin": "2023-03-30"
}}

Pregunta:
{pregunta}
"""
