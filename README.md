🔄 CAMBIOS REALIZADOS DE LA DEMO_1 a la DEMO 2

✅ Consulta real con yfinance
A diferencia de la Demo 1, en esta versión ya conecto con yfinance para calcular el precio medio real de una acción del IBEX 35 entre dos fechas.

🧠 Extracción precisa con LLM
He corregido y afinado el prompt del modelo (PROMPT_API_EXTRAER) para que devuelva correctamente un JSON limpio con la empresa y el rango de fechas.

🔧 Parser robusto
He mejorado la función extract_json para que pueda autocorregir errores menores del modelo (como una llave de cierre faltante), haciendo más estable el flujo.

🌐 Interfaz en Streamlit
He reemplazado la consola por una interfaz gráfica web usando Streamlit, lo que hace que la demo sea más usable y presentable.

🚀 Actualización del modelo LLM
Sustituí el modelo mixtral, que ya no está disponible, por llama3-8b-8192 a través de la API de Groq, que es más moderno y eficiente.

🔄 CAMBIOS REALIZADOS DE LA DEMO_2 a la DEMO_3

✅ Integración de series temporales con modelos reales
En DEMO 3 he incorporado la predicción real mediante modelos pickle (.pkl) por empresa y lag (1, 7 o 15 días). Esto permite al chatbot devolver resultados de predicción basados en modelos entrenados, no solo simulaciones.

✅ Integración del motor RAG con Qdrant
He conectado el sistema a una base vectorial Qdrant, lo que permite realizar búsquedas semánticas en documentos financieros (informes, memorias, resultados). El modelo LLM genera respuestas basadas en los fragmentos encontrados, enriqueciendo las respuestas documentales.

✅ Clasificación automática mediante prompt especializado
La clasificación de cada pregunta del usuario ahora se realiza mediante un prompt específico (PROMPT_CLASIFICACION). El LLM analiza la consulta y decide de forma autónoma si debe activarse el nodo de series temporales, API de precios o RAG con Qdrant.

🔗 Orquestación unificada con LangGraph
He unificado todos los componentes en un flujo orquestado modular mediante LangGraph, facilitando la escalabilidad y el mantenimiento del sistema.

🌐 App de Streamlit con funcionalidad completa
La interfaz en Streamlit ahora soporta consultas de los tres tipos: series temporales, API real (yfinance) y RAG (Qdrant). El usuario recibe una respuesta enriquecida, con fragmentos o gráficos si aplica.


Demo 3 a Demo 3.5


[🌐 Nodo API] Prompt de extracción:

Extrae los siguientes datos de la pregunta sobre **precios de acciones del IBEX 35**:

- **empresa** (en minúsculas)
- **fecha_inicio** (YYYY-MM-DD)
- **fecha_fin** (YYYY-MM-DD)

Extrae los siguientes datos de la pregunta sobre precios de acciones del IBEX 35:

- empresa (en minúsculas, sin tildes ni mayúsculas, sin confundir con otras empresas)
- fecha_inicio (YYYY-MM-DD)
- fecha_fin (YYYY-MM-DD)

Usa la lógica de lenguaje natural para interpretar referencias temporales como "ayer", "la semana pasada", "el lunes", etc. Calcula fechas realistas basadas en hoy (aunque estés simulando).

En este caso, si se menciona una *fecha específica, **usa esa fecha como la fecha de inicio y fin*.

---

Responde **EXCLUSIVAMENTE** en formato JSON, sin explicaciones, texto adicional o puntuación extra.
La respuesta debe ser **SOLAMENTE** el objeto JSON.

**Ejemplo de formato de respuesta:**
{
  "empresa": "iberdrola",
  "fecha_inicio": "2023-03-01",
  "fecha_fin": "2023-03-30"
}

---
**Pregunta del usuario**:
cual fue el precio de iberdrola medio en enero de 2024


[🌐 Nodo API] Respuesta LLM para extracción CRUDA:
'{
  "empresa": "iberdrola",
  "fecha_inicio": "2024-01-01",
  "fecha_fin": "2024-01-31"
}'
[🌐 Nodo API] Datos extraídos del LLM:
{'empresa': 'iberdrola', 'fecha_inicio': '2024-01-01', 'fecha_fin': '2024-01-31'}
[🌐 Nodo API] Empresa normalizada: iberdrola
[🌐 Nodo API] Fechas normalizadas: 2024-01-01, 2024-01-31
[🌐 Nodo API] Prompt de simulación:

Eres un sistema especializado en proporcionar **datos históricos de precios de acciones** del IBEX 35 utilizando la API de **YFinance**.

Tu tarea es consultar el **precio promedio** de la acción de una empresa del IBEX 35 para un **rango temporal** específico que el usuario solicite.

Dado que esta es una consulta a la API de YFinance, simplemente responde con los **datos históricos reales** obtenidos. La API descargará los datos y devolverá el **precio promedio** de la acción en el periodo solicitado.

---

**Pregunta del usuario**:
cual fue el precio de iberdrola medio en enero de 2024

---

⚠️ Devuelve **exclusivamente** la respuesta con el precio promedio obtenido de la API, siguiendo el siguiente formato:

- El precio promedio de las acciones de **[empresa]** entre **[fecha_inicio]** y **[fecha_fin]** fue de **[precio_promedio] €**.

**Ejemplo de formato esperado**:
"El precio promedio de las acciones de **BBVA** entre **2023-03-01** y **2023-03-07** fue de **12.28 €**."

No incluyas ninguna otra información adicional ni interpretación.

[🌐 Nodo API] Respuesta simulada:
El precio promedio de las acciones de Iberdrola entre 2024-01-01 y 2024-01-31 fue de 10.43 €.
⚠️ Error extrayendo respuesta simulada: Error al extraer JSON: No se encontró un bloque JSON en el texto.
Texto recibido:
El precio promedio de las acciones de Iberdrola entre 2024-01-01 y 2024-01-31 fue de 10.43 €.

📊 Resultado bruto de YFinance para IBE.MC (2024-01-01 a 2024-02-01):
Price           Close       High        Low       Open    Volume
Ticker         IBE.MC     IBE.MC     IBE.MC     IBE.MC    IBE.MC
Date
2024-01-02  11.142534  11.325506  11.081544  11.259824  12175208
2024-01-03  11.105000  11.241056  11.095617  11.189449  10708600
2024-01-04  11.287972  11.306739  11.151917  11.151917  17462323
2024-01-05  11.292664  11.320813  11.151916  11.212906  10171410
2024-01-08  11.255131  11.330196  11.222290  11.250439  14466437
2024-01-09  11.109109  11.237951  11.061389  11.204547  10503260
2024-01-10  11.075705  11.123424  11.056617  11.118652  12543567
2024-01-11  10.994583  11.180689  10.985039  11.118653   9003574
2024-01-12  11.142514  11.152058  11.047075  11.047075   7794136
2024-01-15  11.132969  11.137741  11.032758  11.109109  17633594
2024-01-16  11.023215  11.109111  11.023215  11.099566   9228465
2024-01-17  10.927775  10.975495  10.875285  10.975495  11832891
2024-01-18  10.751213  10.889599  10.736897  10.875284  11463479
2024-01-19  10.708265  10.755985  10.646229  10.717809  10024791
2024-01-22  10.746441  10.775072  10.660546  10.722581   5955382
2024-01-23  10.546020  10.732125  10.546020  10.703494  18914062
2024-01-24  10.617598  10.660545  10.546018  10.550791   8548141
2024-01-25  10.565106  10.651002  10.503071  10.651002   8100965
2024-01-26  10.469667  10.674862  10.426720  10.588966  10689636
2024-01-29  10.517387  10.526931  10.407632  10.488755  18069394
2024-01-30  10.588967  10.627143  10.464896  10.512616   7862563
2024-01-31  10.665318  10.708265  10.546019  10.584194  12538956
[🌐 Nodo API] Resultado de la API financiera:
✅ El precio medio de las acciones de Iberdrola entre 2024-01-01 y 2024-01-31 fue de Ticker
IBE.MC    10.89
dtype: float64 €.
[🌐 Nodo API] Respuesta final combinada:
(No se pudo generar una respuesta simulada del LLM)

📊 Datos reales:
✅ El precio medio de las acciones de Iberdrola entre 2024-01-01 y 2024-01-31 fue de Ticker
IBE.MC    10.89
dtype: float64 €.

--------------------------------------

[🌐 Nodo API] Respuesta simulada:
El precio promedio de las acciones de **Iberdrola** entre **2024-01-04** y **2024-01-04** fue de **6.43 €**.
⚠️ Error extrayendo respuesta simulada: Error al extraer JSON: No se encontró un bloque JSON en el texto.
Texto recibido:
El precio promedio de las acciones de **Iberdrola** entre **2024-01-04** y **2024-01-04** fue de **6.43 €**.

📊 Resultado bruto de YFinance para IBE.MC (2024-01-03 a 2024-01-06):
Price           Close       High        Low       Open    Volume
Ticker         IBE.MC     IBE.MC     IBE.MC     IBE.MC    IBE.MC
Date
2024-01-03  11.105000  11.241056  11.095617  11.189449  10708600
2024-01-04  11.287972  11.306739  11.151917  11.151917  17462323
2024-01-05  11.292664  11.320813  11.151916  11.212906  10171410

📌 Datos filtrados para 2024-01-04:
Price           Close       High        Low       Open    Volume
Ticker         IBE.MC     IBE.MC     IBE.MC     IBE.MC    IBE.MC
Date
2024-01-04  11.287972  11.306739  11.151917  11.151917  17462323
[🌐 Nodo API] Resultado de la API financiera:
✅ El precio de cierre de las acciones de Iberdrola el 2024-01-04 fue de Ticker
IBE.MC    11.29
Name: 2024-01-04 00:00:00, dtype: float64 €.
[🌐 Nodo API] Respuesta final combinada:
(No se pudo generar una respuesta simulada del LLM)

📊 Datos reales:
✅ El precio de cierre de las acciones de Iberdrola el 2024-01-04 fue de Ticker
IBE.MC    11.29
Name: 2024-01-04 00:00:00, dtype: float64 €.

------

🤖 Chatbot Financiero IBEX 35
Consulta precios históricos de acciones del IBEX 35 o analiza documentos financieros usando lenguaje natural.

🧑 Tú:

cual fue el precio de iberdrola el 4 de enero de 2024 

Bot (Fuente: api)

(No se pudo generar una respuesta simulada del LLM)

📊 Datos reales: ✅ El precio de cierre de las acciones de Iberdrola el 2024-01-04 fue de Ticker IBE.MC 11.29 Name: 2024-01-04 00:00:00, dtype: float64 €.

📝 Historial de la conversación
Tú: cual fue el precio de iberdrola medio en enero de 2024

Bot (Fuente: api): (No se pudo generar una respuesta simulada del LLM)

📊 Datos reales: ✅ El precio medio de las acciones de Iberdrola entre 2024-01-01 y 2024-01-31 fue de Ticker IBE.MC 10.89 dtype: float64 €.

Tú: cual fue el precio de iberdrola el 4 de enero de 2024

Bot (Fuente: api): (No se pudo generar una respuesta simulada del LLM)

📊 Datos reales: ✅ El precio de cierre de las acciones de Iberdrola el 2024-01-04 fue de Ticker IBE.MC 11.29 Name: 2024-01-04 00:00:00, dtype: float64 €.