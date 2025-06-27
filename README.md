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

 
 demo 6 conversacioonal 