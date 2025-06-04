🔄 CAMBIOS REALIZADOS DEL MAIN A LA DEMO_1

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

🔄 CAMBIOS REALIZADOS DE LA DEMO_1 a la DEMO_2
