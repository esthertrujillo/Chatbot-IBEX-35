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


🔄NUEVOS CAMBIOS REALIZADOS EN LA DEMO_1 

✅ Impresión detallada del cálculo del precio
Ahora se muestra paso a paso cómo se calcula el precio medio:
- Se imprime el dataframe crudo (RAW DATA) recibido de yfinance.
- Se listan las fechas reales disponibles en ese rango.
- Se muestra el cálculo final de la media.
Esto ayuda a auditar y entender el comportamiento real del sistema.

📅 Gestión de expresiones como “hoy”, “ayer”, “anteayer”…
Se añadió un bloque de contexto al prompt para que el modelo interprete correctamente fechas relativas como:
"¿Cuánto vale Telefónica hoy?"
"¿A cuánto cerró Iberdrola ayer?"
Esto se logra pasando la fecha actual (hoy) al prompt y dejando que el modelo genere las fechas correctas en formato YYYY-MM-DD.

🧠 Mejoras en el prompt de extracción (PROMPT_API_EXTRAER)
El prompt ahora contiene una instrucción adicional para que el modelo asuma el año actual si no se especifica y para que maneje expresiones como "ayer" o "hoy".

🔁 Función consultar_precio_medio mejorada
Ahora devuelve una tupla con el precio medio y la fecha real utilizada.
Esto permite identificar si la fecha solicitada no estaba disponible y se usó una alternativa próxima (como en fines de semana).

Pasos Futuros
- Que tenga memoria el chat bot (por detras se repite la pregunta, y si muestra la 2da) aun no
- Que la eleccion es si es serie temporal, api o rag lo haga un prompt (nodo clasificar)
    - hago un nodo y un prompt que lo clasifique (proporcionar ejemplos)
- una tool para noticias (yahoo finance) que recurra a el cuando la pregunta lo precise
    - 
- seguir adaptando las posibles formas de referirse a el "tiempo" (ayer, hoy...)
