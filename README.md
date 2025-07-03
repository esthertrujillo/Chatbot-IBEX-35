# Chatbot Financiero IBEX 35

Este proyecto implementa un chatbot financiero interactivo centrado en el mercado IBEX 35. La solución permite realizar consultas sobre cotizaciones históricas, predicciones de precios futuros y recuperación de información financiera relevante. La arquitectura del sistema está basada en agentes inteligentes orquestados mediante grafos de estado utilizando LangGraph, lo que proporciona flexibilidad y adaptabilidad en la conversación con el usuario. La interfaz ha sido desarrollada con Streamlit para ofrecer una experiencia intuitiva y accesible.

## Características Principales

El sistema está diseñado para ofrecer funcionalidades clave que cubren diferentes necesidades de análisis financiero:

- **Consulta de Precios Históricos**  
  Permite recuperar cotizaciones históricas de empresas del IBEX 35 mediante la API de yfinance.

- **Análisis Documental (RAG)**  
  Integra un sistema de recuperación aumentada de información (RAG) basado en embeddings semánticos y una base de datos vectorial construida con Qdrant, que permite acceder a contenidos relevantes de informes financieros, presentaciones de resultados y memorias anuales.

- **Predicción de Series Temporales**  
  Incluye modelos preentrenados de predicción de precios de cierre para distintas empresas, basados en algoritmos como XGBoost y LightGBM. Las predicciones se visualizan directamente en la interfaz.

- **Gestión de Historial de Conversación**  
  El sistema conserva el contexto conversacional a lo largo de la sesión, lo que permite respuestas más coherentes y personalizadas.

- **Interfaz Web Interactiva**  
  Desarrollada en Streamlit, permite al usuario interactuar de forma sencilla, visual y eficiente, sin necesidad de conocimientos técnicos.

## Tecnologías Utilizadas

Este proyecto combina tecnologías avanzadas en procesamiento de lenguaje natural, recuperación de información y modelado predictivo:

- Python 3.13.5 como lenguaje principal de desarrollo.
- Streamlit para la creación de la interfaz web.
- LangChain y LangGraph para la orquestación de agentes conversacionales mediante grafos de estado.
- Groq API para la integración de un modelo de lenguaje (LLM) de alto rendimiento (`llama3-8b-8192`) con baja temperatura.
- Qdrant como base de datos vectorial para el sistema de recuperación aumentada.
- Sentence-Transformers (`intfloat/e5-large-v2`) para la generación de embeddings semánticos.
- yfinance para la obtención de datos financieros históricos.
- Bibliotecas como scikit-learn, pandas, NumPy, matplotlib, seaborn, joblib, XGBoost y LightGBM para la creación, entrenamiento y visualización de modelos de predicción.
- python-dotenv para la gestión de claves y variables de entorno.

## Estructura del Proyecto

Chatbot-IBEX-35/
├ .env
├ README.md
├ requirements.txt
├ app.py
├ main.py
├ prompts.py
├ cotizaciones.py
├ qdrant_utils.py
├ series_model.py
├ data/
│ └ IBEX35_cotizaciones_20_Limpio.csv
├ modelos_por_empresa/
│ ├ BBVA_lag1.pkl
│ └ ...
└ utils/
├ init.py
└ series_utils/
├ preprocessing.py
├ features.py
├ scaling.py
├ model_training.py
└ visualization.py


## Arquitectura del Sistema

El núcleo del sistema está definido mediante una arquitectura modular basada en grafos de estado, implementada con la librería LangGraph. Esta estructura permite una navegación no lineal entre nodos especializados, cada uno de los cuales representa una etapa en el procesamiento de la consulta del usuario.

Los nodos principales del flujo son:

- **Input**  
  Entrada de la consulta del usuario. Se conecta con el primer nodo funcional del grafo.

- **Clasificación (`classify_ticket`)**  
  Determina la intención de la consulta (precio histórico, predicción o recuperación documental).

- **Consulta de Datos de API (`get_api_data`)**  
  Extrae información de cotizaciones históricas a través de yfinance.

- **Predicción de Series Temporales (`predict_price`)**  
  Ejecuta un modelo de predicción para estimar el valor futuro de una acción.

- **Recuperación Documental RAG (`get_rag_response`)**  
  Realiza una búsqueda semántica en documentos relevantes mediante Qdrant y embeddings.

- **Gestión de Memoria y Estado (`update_ticket_memory`)**  
  Almacena el contexto de la conversación en la estructura central `TicketState`.

- **Output (`final_output`)**  
  Genera y devuelve la respuesta final al usuario utilizando el LLM.

## Ejecución del Proyecto

Para ejecutar el chatbot de forma local, se deben seguir los siguientes pasos:

1. Clonar el repositorio del proyecto.
2. Instalar las dependencias necesarias incluidas en `requirements.txt`.
3. Crear un archivo `.env` con las credenciales necesarias (Groq API Key, URL de Qdrant, etc.).
4. Ejecutar la aplicación mediante:

```bash
streamlit run app.py
