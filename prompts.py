PROMPT_CLASIFICACION = """
Actúa como un sistema de clasificación de preguntas financieras relacionadas con empresas del IBEX 35.

Tu tarea es leer una pregunta del usuario y clasificarla en **una y solo una** de las siguientes categorías:

- "series_temporales" → si pregunta por la evolución, rendimiento, estabilidad o tendencia de una acción en el tiempo.
- "documentos_financieros" → si hace referencia a beneficios, informes, resultados, cuentas, deuda, EBITDA, memorias o aspectos contables.
- "consulta_api" → si pide directamente el precio medio, actual o promedio de una acción en un rango de fechas, sin análisis adicional.

🟨 Devuelve únicamente el nombre exacto de la categoría:  
**series_temporales**, **documentos_financieros**, o **consulta_api**  
No escribas comillas, ni texto adicional.

---

### Ejemplos:

**Pregunta:** ¿Cómo ha evolucionado Repsol en el último año?  
**Respuesta:** series_temporales

**Pregunta:** ¿Qué beneficios obtuvo BBVA en 2023?  
**Respuesta:** documentos_financieros

**Pregunta:** ¿Cuál fue el precio medio de Iberdrola en abril de 2022?  
**Respuesta:** consulta_api

---

**Pregunta del usuario:**
{pregunta}
"""


PROMPT_RAG_DOCUMENTOS = """
Actúa como un asistente especializado en interpretar información contenida en informes anuales y memorias de empresas del IBEX 35.

A continuación tienes fragmentos relevantes de dichos documentos:

{contexto}

Con base en estos fragmentos, responde de forma precisa y clara a la siguiente pregunta del usuario:
"{pregunta}"

✅ Usa Markdown para formatear la respuesta:
- Presenta los beneficios como una lista de puntos con • (bullet).
- Usa **negritas** para resaltar conceptos clave como tipos de beneficio, fechas o importes.

⚠️ Devuelve EXCLUSIVAMENTE un objeto JSON con la clave "respuesta".
Ejemplo:
{{
  "respuesta": "• **Reparto en efectivo:** 0,16 euros brutos por acción en octubre (952 millones de euros).\n• **Recompra de acciones:** 781 millones de euros."
}}
"""



PROMPT_SERIES = """
Actúa como un analista financiero experto en series temporales de acciones del IBEX 35.

Tu tarea es:
1. Analizar la pregunta del usuario para entender qué empresa del IBEX 35 menciona.
2. Inferir si se refiere a una evolución reciente (1 día), semanal (7 días) o más larga (15 días).
3. Simular una respuesta basada en el comportamiento de la acción en ese período, aunque no tengas acceso directo a los datos.

Pregunta del usuario:
{pregunta}

Devuelve un objeto JSON con la clave "respuesta", por ejemplo:
{{
  "respuesta": "Acciona Energía ha mostrado una tendencia bajista en la última semana, con un ligero repunte en los últimos dos días."
}}
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

---
Pregunta del usuario:
{pregunta}

---
⚠️ Devuelve **exclusivamente** un objeto JSON, sin ningún texto antes ni después.

Formato de ejemplo:
{{
  "respuesta": "El precio actual de las acciones de Banco Santander es 3,92€, con una variación diaria de +0,85%."
}}

"""


PROMPT_API_EXTRAER = """
Extrae los siguientes datos de la pregunta sobre precios de acciones del IBEX 35:

- empresa (en minúsculas, sin tildes ni mayúsculas)
- fecha_inicio (YYYY-MM-DD)
- fecha_fin (YYYY-MM-DD)

Usa la lógica de lenguaje natural para interpretar referencias temporales como "ayer", "la semana pasada", "el lunes", etc. Calcula fechas realistas basadas en hoy (aunque estés simulando).

---
Pregunta:
a cuanto cotizó telefonica la semana pasada

---
⚠️ Devuelve EXCLUSIVAMENTE un objeto JSON, sin ningún texto antes ni después.

🛑 No copies el ejemplo siguiente literalmente. Solo es un ejemplo de formato:

{{
  "empresa": "iberdrola",
  "fecha_inicio": "2023-03-01",
  "fecha_fin": "2023-03-30"
}}
"""