## 🧪 Demo 1 – Chatbot Financiero IBEX 35 (versión inicial)

Esta demo muestra la **primera versión funcional** del chatbot financiero centrado en empresas del IBEX 35, combinando procesamiento de lenguaje natural con acceso a datos reales mediante `yfinance`.

### 🎯 ¿Qué hace esta demo?

- Permite al usuario **hacer preguntas por consola** relacionadas con:
  - 📈 Cotizaciones históricas de acciones.
  - 📊 Simulación de análisis de series temporales.
  - 📑 Simulación de extracción de información de informes financieros.

- Utiliza un flujo modular con **LangGraph**, que:
  1. Clasifica automáticamente la intención de la pregunta (`series_temporales`, `documentos_financieros`, o `consulta_api`).
  2. Redirige la consulta al módulo correspondiente:
     - `yfinance` para obtener el precio medio de una acción entre fechas.
     - Un modelo LLM de Groq (Mixtral) para simular respuestas sobre tendencias o informes.
  3. Devuelve una respuesta estructurada indicando la **fuente utilizada** (`api`, `documentos`, `series_temporales`).

### ⚙️ Componentes clave

- **`app.py`**: Interfaz principal por consola.
- **`main_graph.py`**: Define el grafo conversacional y nodos de procesamiento.
- **`cotizaciones.py`**: Funciones para consultar datos financieros reales con `yfinance`.
- **`prompts.py`**: Contiene los prompts utilizados para cada tipo de pregunta.
- **`test_yfinance.py`**: Verificación manual de la descarga de precios históricos desde Yahoo Finance.

### 🧠 Lógica de clasificación (ejemplos):

| Pregunta | Clasificación automática | Acción |
|---------|--------------------------|--------|
| ¿Cuál fue el precio medio de Repsol en marzo? | `consulta_api` | Consulta real con `yfinance` |
| ¿Cómo ha evolucionado Telefónica en el último año? | `series_temporales` | Simulación con LLM |
| ¿Qué dice el informe anual de BBVA sobre beneficios? | `documentos_financieros` | Simulación con LLM |

---

Esta demo sirve como **base para futuras versiones** donde se integrarán análisis más avanzados y documentos reales con Quadrant.
