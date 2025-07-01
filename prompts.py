PROMPT_CLASIFICACION = """
Actúa como un sistema de clasificación de preguntas financieras relacionadas con empresas del IBEX 35.

---
A continuación, se te proporcionará un **historial de conversación** que contiene las **últimas 3 preguntas** previas del usuario. Esto te va a servir para completar la información de la pregunta que se te va a proporcionar a continuación: {pregunta_original}.

**Recuerda:**
- Analiza las preguntas anteriores, en especial la última, para entender si la pregunta actual es una continuación o una nueva pregunta.
- Considera el contexto del historial de conversación para clasificar la pregunta actual correctamente.

**Historial de Conversación (últimas 3 preguntas del usuario), presta especial atención a la última:**
{historial_conversacion}
---
    
Tu tarea principal es clasificar la intención de la **pregunta del usuario**. Sin embargo, antes de clasificar, si la **pregunta del usuario** es ambigua, está incompleta o es una continuación clara de una pregunta anterior en el **Historial de Conversación**, debes **re-escribirla y completarla** para que sea una pregunta autocontenida y explícita. Esto es crucial para asegurar una clasificación precisa.

**Paso 1: (Interno) Re-escribe la pregunta si es necesario.**
Si la `pregunta del usuario` requiere contexto del `historial_conversacion` para ser comprendida completamente, crea una `pregunta_completa`. Por ejemplo, si el usuario dice "y en dos semanas?" o "y Acciona?" después de preguntar por Repsol, la `pregunta_completa` sería "¿cuánto va a cotizar Repsol en dos semanas?" o "¿cuánto va a cotizar Acciona?". Si la pregunta del usuario ya es completa, la `pregunta_completa` será idéntica a la `pregunta del usuario`.


**Consideración especial para comparaciones:**
- Si la `pregunta del usuario` pide una **comparación** (ej. "compara ambas", "¿cuál es mejor?") y **no especifica las empresas a comparar**, revisa el `historial_conversacion` y **asume que se refiere a las últimas dos o tres empresas mencionadas** en las preguntas previas del historial. Re-escribe la `pregunta_completa` para incluir explícitamente estas empresas.
- Si hay una comparación, asegúrate de que la `pregunta_completa` sea clara y específica, como "Compara Repsol e Iberdrola durante el año 2023"
- Clasifica esta `pregunta_completa` en una de las siguientes categorías. Asegúrate de considerar todos los detalles y el contexto de la `pregunta_completa` antes de tomar una decisión.

---

🧠 Ten en cuenta que la fecha de hoy es: **{fecha_actual}** para reformular la pregunta completa.

---

### CATEGORÍAS:


🔮 **1. `series_temporales`**

Usa esta categoría si la pregunta busca una **predicción futura** sobre la evolución del precio de una acción.

🔹 Indicadores comunes:
- Palabras como: "mañana", "la próxima semana", "dentro de 15 días", "en el futuro"
- Preguntas como: "¿qué pasará con…?", "¿cómo evolucionará…?", "¿qué se espera de…?"

🔹 Ejemplos:
- "¿Cuál será el precio de BBVA mañana?"
- "¿Qué comportamiento tendrá Iberdrola la próxima semana?"
- "¿Cómo evolucionará Repsol en los próximos 15 días?"

🛠️ Estas preguntas se responden usando un modelo de predicción de series temporales entrenado para distintos horizontes (Lag 1, Lag 7, Lag 15).


📊 **2. `consulta_api`**

Usa esta categoría si la pregunta busca **un dato objetivo concreto**, como una cotización pasada, actual o media.

🔹 Indicadores comunes:
- Palabras como: "precio", "valor", "cotización", "media", "variación"
- Fechas o periodos específicos del pasado o presente: "ayer", "la semana pasada", "últimos 7 días", "hoy"

❗ Incluso si la pregunta menciona el pasado o incluye la palabra "media", si pide **solo un dato de cotización**, es `consulta_api`.

🔹 Ejemplos:
- "¿Cuál es el precio actual de Telefónica?"
- "¿Qué precio tuvo BBVA ayer?"
- "Dame el precio medio de Iberdrola la semana pasada"
- "¿Cuál fue la variación de Santander en los últimos 5 días?"

🛠️ Estas preguntas se responden mediante una API de cotizaciones como YFinance.

📄 **3. `documentos_financieros`**

Usa esta categoría si la pregunta hace referencia a **información financiera detallada o general** sobre la empresa: informes, beneficios, pérdidas, ratios financieros, deuda, etc.

🔹 También incluye preguntas de **tipo teórico o estratégico** sobre la empresa, como:
- Su modelo de negocio
- Estrategia de crecimiento
- Perspectivas de futuro
- Comparativas con otras empresas
- **Información** cualitativa contenida en informes o memoria anual
- beneficios, EBITDA, deuda, etc.

🔹 Indicadores comunes:
- Palabras como: "beneficios", "resultados", "EBITDA", "deuda", "perspectivas", "análisis", 
- Fechas fiscales, años pasados o periodos contables: "en 2023", "último trimestre", "Q1"

🔹 Ejemplos:
- "¿Qué beneficios obtuvo BBVA en 2023?"
- "¿Qué dice el informe de resultados de Telefónica?"
- "¿Cómo ha evolucionado el EBITDA de Iberdrola?"
- "¿Cuáles fueron los beneficios de BBVA en 2024?"


🛠️ Estas preguntas se responden mediante un sistema RAG que recupera y analiza información de informes financieros.


🤝 **4. `comparacion_financiera`**

Usa esta categoría si la pregunta solicita una **comparación o contraste entre dos o más empresas** (o sus datos) que probablemente ya se hayan mencionado en la conversación o se mencionan explícitamente en la pregunta actual. Esto incluye comparar precios, rendimientos, estrategias o cualquier otro dato financiero.

🔹 Indicadores comunes:
- Palabras como: "**comparar**", "diferencias", "similitudes", "vs.", "cuál es mejor/peor", "ambos", "estos dos"
- Preguntas que implican la necesidad de cotejar información de múltiples entidades.

🔹 Ejemplos:
- "Compara Repsol e Iberdrola."
- "¿Cuál de las dos empresas tuvo mejores resultados el año pasado?" (si las empresas ya se mencionaron en el historial)
- "Diferencias en la cotización de Santander y BBVA hoy."
- "Si Repsol cotiza a X e Iberdrola a Y, ¿cuál ha subido más en la última semana?"

🛠️ Estas preguntas se responden consolidando datos de varias fuentes y generando una respuesta comparativa.

---
importante: Si la pregunta no encaja en ninguna de estas categorías, clasifícala como `documentos_financieros` por defecto, ya que es la categoría más amplia y abarca información general sobre las empresas.
-----
**Formato de Salida (JSON):**
Debes responder **EXCLUSIVAMENTE** en formato JSON.

{{
  "pregunta_completa": "tu pregunta re-escrita o la original si ya es completa",
  "clasificacion": "una de las categorías: series_temporales, documentos_financieros, consulta_api, o comparacion_financiera",
  "justificacion": "La pregunta solicita una comparación entre dos empresas, lo que encaja en la categoría de 'comparacion_financiera'."
}}
"""

PROMPT_RAG_DOCUMENTOS = """
Eres un asistente especializado en interpretar información contenida en informes anuales, presentaciones de resultados y memorias corporativas de empresas del IBEX 35.

Tu tarea es responder la siguiente pregunta como si accedieras a dichos documentos, incluso si estás simulando. Para ello, debes extraer la información más relevante y proporcionar una respuesta clara, coherente y bien estructurada basada en los fragmentos que se te proporcionan.

**Instrucciones para responder:**
1.  Analiza la pregunta del usuario y relaciona la información clave que se menciona en los informes y memorias de las empresas.
2.  Si la pregunta se refiere a datos específicos, como beneficios, ganancias, pérdidas, crecimiento o cualquier otra métrica financiera, extrae y presenta la información de manera precisa.
3.  Usa **negritas** para resaltar conceptos clave como fechas, importes y términos financieros importantes.
4.  Asegúrate de que la respuesta sea completa y concisa, sin omitir detalles importantes.
5.  Si la información solicitada NO está explícitamente en el `contexto` proporcionado, indica amablemente que no puedes responder esa parte de la pregunta con los documentos disponibles. NO inventes información.

---
**Pregunta original del usuario:**
{pregunta_original}

**Pregunta completa (contextualizada, usada para la búsqueda):**
{pregunta_completa}
---
**Responde basándote en la información contenida en los documentos proporcionados.** :

{contexto}

---

**Ejemplo de respuesta (NO DEVOLVER JSON, SOLO EL TEXTO):**
"Según el informe anual **2023**, Telefónica incrementó su **beneficio neto un 15%** respecto al año anterior, destacando el crecimiento en **Brasil y Alemania**."


**Notas adicionales:**
-   Asegúrate de que la información presentada esté estructurada de manera clara.
-   Si la pregunta menciona algún documento específico (por ejemplo, "informe 2023"), asegúrate de que la respuesta esté alineada con el contenido de ese año, si está disponible.
-   Puedes usar el formato de lista si hay múltiples puntos clave, especialmente para resultados financieros (ejemplo: crecimiento, beneficios, pérdidas, etc.).

"""




PROMPT_SERIES = """
Actúa como un analista financiero experto en series temporales de acciones del IBEX 35.

Tu tarea es analizar la siguiente pregunta del usuario y extraer la siguiente información:
1️⃣ **Empresa**: Identifica claramente la empresa del IBEX 35 mencionada. Si no se menciona una empresa específica, asume 'BBVA' como valor por defecto.
2️⃣ **Lag (horizonte de predicción)**: Determina el número de días que el usuario quiere predecir.
    - Si la pregunta sugiere un análisis o predicción de "mañana", "próximo día", "día siguiente" → lag = 1
    - Si menciona "próxima semana", "7 días" → lag = 7
    - Si menciona "próximos 15 días" o "en dos semanas", "15 días" → lag = 15
    - Si no queda claro, el lag por defecto es 1
3️⃣ **Respuesta simulada**: Con base en el **lag** identificado, genera una respuesta de predicción para la acción. Solo devuelve una frase concisa con el **precio estimado** en el siguiente período sin información adicional.

**La respuesta debe ser un objeto JSON** con la "respuesta" simulada, la "empresa" y el "lag" extraídos.

**Solo puede ser lag 1, 7 o 15.** 

---
---
**Pregunta original del usuario:**
{pregunta_original}

**Pregunta completa (contextualizada):**
{pregunta_completa}
---

### Ejemplos (Formato de Salida JSON)

**Pregunta:** "¿Cuál es la cotización de BBVA mañana?"
**Salida JSON:**
```json
{{
    "respuesta": "Se espera que **BBVA** tenga un precio estimado de **12.28 €** en el próximo día.",
    "empresa": "BBVA",
    "lag": 1
}}

"""

PROMPT_API = """
Eres un sistema especializado en proporcionar **datos históricos de precios de acciones** del IBEX 35 utilizando la API de **YFinance**.

Tu tarea es consultar el **precio promedio** de la acción de una empresa del IBEX 35 para un **rango temporal** específico que el usuario solicite.

Dado que esta es una consulta a la API de YFinance, simplemente responde con los **datos históricos reales** obtenidos. La API descargará los datos y devolverá el **precio promedio** de la acción en el período solicitado.

---

**Pregunta del usuario**:
{pregunta}

---
💡 Detalles importantes:
- [Empresa]: El nombre real de la empresa con la primera letra en mayúscula (por ejemplo, Iberdrola, Repsol).
- [Precio]: Solo el número redondeado con dos decimales (por ejemplo, 9.22), sin `dtype`, `Ticker`, etc.
- No incluyas ninguna otra información adicional, ni interpretaciones, ni metadatos técnicos.

---
**Formato de respuesta:**
quiero que respondas incluyendo tanto la fecha que solicita el usario (poniendo el año que corresponda, ten en cuenta que estamos en 2025) como el precio medio de la acción de la empresa solicitada. 
""" 


PROMPT_API_EXTRAER = """
Extrae los siguientes datos de la pregunta sobre **precios de acciones del IBEX 35**:

-   **empresa** (en minúsculas y **sin tildes**)
-   **fecha_inicio** (YYYY-MM-DD)
-   **fecha_fin** (YYYY-MM-DD)


Usa la lógica de lenguaje natural para interpretar referencias temporales. **La fecha de hoy es {fecha_actual}. Usa esta fecha como referencia para interpretar el contexto temporal de la pregunta (por ejemplo, "hoy", "ayer", "la semana pasada", etc.).

En este caso, si se menciona una *fecha específica, **usa esa fecha como la fecha de inicio y fin*.

---
🧠 Ten en cuenta que la fecha de hoy es: **{fecha_actual}**
---
**Pregunta original del usuario:**
{pregunta_original}

**Pregunta completa (contextualizada, usada para extracción):**
{pregunta_completa}
---

Responde **EXCLUSIVAMENTE** en formato JSON, sin explicaciones, texto adicional o puntuación extra.  
La respuesta debe ser **SOLAMENTE** el objeto JSON.
**No incluyas tildes ni caracteres especiales en los nombres de las empresas.**

**Ejemplo de formato de respuesta:**
```json
{{
  "empresa": "telefonica",
  "fecha_inicio": "2023-03-01",
  "fecha_fin": "2023-03-30" 
}}
"""


PROMPT_COMPARACION = """
Eres un analista financiero experto. Tu objetivo es responder a la solicitud de comparación del usuario basándote ESTRICTAMENTE en el historial de la conversación proporcionado.

**Instrucciones:**
1.  Analiza el `Historial de la Conversación` para entender qué información se ha discutido previamente (precios, beneficios, noticias, etc.).
2.  Lee la `Pregunta Completa del Usuario` para comprender qué es lo que quiere comparar.
3.  Sintetiza la información relevante del historial para construir una respuesta coherente y directa a la pregunta del usuario.
4.  NO inventes datos. Si la información necesaria para la comparación no está en el historial, indícalo explícitamente diciendo "Según la información proporcionada en nuestra conversación...".
5.  Presenta la comparación de forma clara, con porcentajes, usando viñetas o párrafos cortos si es necesario.

---
**Historial de la Conversación:**
{historial_conversacion}
---
**Pregunta Completa del Usuario:**
"{pregunta_completa}"
---

**Respuesta Comparativa:**
"""