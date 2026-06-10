# CS2 Market Sentiment Index

## Tabla de Contenidos
1. [Descripción del Proyecto](#descripción-del-proyecto)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Stack Tecnológico](#stack-tecnológico)
4. [Estructura del Proyecto](#estructura-del-proyecto)
5. [Instrucciones de Despliegue](#instrucciones-de-despliegue)
6. [Funcionalidades Implementadas](#funcionalidades-implementadas)
7. [Desarrollo Local](#desarrollo-local)
8. [Configuración Adicional](#configuración-adicional)

---

## Descripción del Proyecto

Este proyecto es una herramienta de análisis financiero impulsada por Inteligencia Artificial que evalúa en tiempo real el sentimiento del mercado de skins e items de Counter-Strike 2. La aplicación extrae datos de la comunidad, los procesa mediante algoritmos de Procesamiento de Lenguaje Natural (NLP) y presenta un dashboard analítico para determinar tendencias de mercado (Alcistas, Bajistas o Neutrales).

---

## Arquitectura del Sistema

El sistema opera bajo un flujo de datos lineal y de procesamiento en tiempo real:

* **Módulo de Extracción de Datos:** Script integrado que realiza peticiones HTTP a la API JSON de Reddit para extraer posts y comentarios de `r/csgomarketforum` basándose en filtros de tiempo y relevancia.
* **Motor de Inteligencia Artificial:** Integración con la API de Google Generative AI (Gemini Pro/Flash). Utiliza técnicas de Prompt Engineering para obligar al LLM a devolver un JSON estructurado con la clasificación de sentimiento financiero.
* **Frontend y Visualización:** Interfaz de usuario Single-Page construida con Streamlit, apoyada por Plotly para el renderizado de gráficos y Pandas para la estructuración de tablas de datos.

---

## Stack Tecnológico

### Backend y Lógica de Datos
* Python 3
* Google Generative AI API (Modelos Gemini Flash/Pro) para NLP
* Pandas (>=2.0.0) para manipulación de DataFrames
* Requests para conexiones a APIs externas

### Frontend y UI
* Streamlit (>=1.30.0) como framework de aplicación web
* Plotly (>=5.18.0) para la renderización de Gauge Charts
* JSON y expresiones regulares (Regex) para el parseo de respuestas del LLM

### Resumen de Tecnologías

| Componente | Tecnologías | Uso Principal |
| :--- | :--- | :--- |
| UI & Dashboard | Streamlit + Plotly | Renderizado web y gráficos interactivos |
| Data Scraping | Python + Requests API | Extracción de datos de Reddit en tiempo real |
| Procesamiento IA | Google Gemini API | Análisis de sentimiento y resúmenes |
| Estructuración | Pandas + JSON | Organización de datos en tablas para la UI |

---

## Estructura del Proyecto

```text
cs2-sentiment-analyzer/
├── app.py                  # Aplicación principal y lógica de negocio
├── requirements.txt        # Dependencias del proyecto
└── .streamlit/             # Configuración del entorno de Streamlit
    ├── config.toml         # Configuración del tema visual (Dark Mode)
    └── secrets.toml        # Variables de entorno y claves de API
