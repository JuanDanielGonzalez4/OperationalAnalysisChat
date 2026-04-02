# Chat de Análisis Operacional

Este proyecto es una herramienta avanzada de análisis de datos operacionales que permite a los usuarios interactuar con hojas de cálculo (Excel) utilizando lenguaje natural. La aplicación utiliza IA para transformar preguntas en consultas de datos precisas y visualizaciones.

## Prerrequisitos

Para ejecutar este proyecto, asegúrate de tener instalado:

- **Python 3.13+**
- **uv** (manejador de paquetes de Python)
- Una **OpenAI API Key** válida.

## Cómo Levantar el Proyecto

1. **Clonar el repositorio:**

   ```bash
   git clone <url-del-repositorio>
   cd chat_operation_analysis
   ```
2. **Instalar dependencias y preparar el entorno:**

   ```bash
   uv sync
   ```
3. **Configurar variables de entorno:**
   Crea un archivo `.env` en la raíz del proyecto con el siguiente contenido:

   ```env
   OPENAI_API_KEY=tu_api_key_aqui
   ```
4. **Ejecutar la aplicación:**

   ```bash
   uv run python main.py
   ```

   La aplicación estará disponible en `http://localhost:8000`.

## Estructura del Proyecto

- `main.py`: Punto de entrada de la aplicación FastAPI.
- `src/agent/`: Contiene la lógica del agente de LangGraph y la integración con Pandas.
- `src/api/`: Definición de los endpoints de la API (Chat, Sesiones).
- `src/data/`: Lógica para cargar y procesar los archivos de datos (Excel).
- `static/`: Frontend de la aplicación (HTML, CSS, JS).
- `data/`: Directorio que contiene el archivo `data.xlsx` con la información operacional y la base de datos de sesiones.

## Modelos y Tecnologías Usadas

- **Framework Web:** [FastAPI].
- **Modelo de Lenguaje:** **GPT-4.1-mini** (vía OpenAI). Ofrece un equilibrio óptimo entre razonamiento complejo y latencia/costo.
- **Orquestación:** [LangGraph] Utilizado para gestionar el estado de la conversación y la persistencia de sesiones mediante SQLite.
- **Agente de Análisis:** [LangChain Pandas Agent].

### ¿Por qué el Agente de Pandas de LangChain?

Se seleccionó este componente específico porque es capaz de **construir código de pandas dinámicamente y ejecutarlo**. Esto permite responder al usuario de manera precisa sin necesidad de enviar todo el contenido de los archivos Excel al prompt (sin "quemar" el contexto). Solo se envía el esquema de los datos, y el agente decide qué operaciones realizar sobre los DataFrames de forma local.

## Sistema de Insights Automaticos

El reporte de insights se genera en dos fases: deteccion deterministica (Pandas/NumPy, sin LLM) y narracion ejecutiva (GPT-4.1-mini). Los detectores operan sobre las columnas semanales `L8W_ROLL` a `L0W_ROLL` de `df_metrics`.

### Detectores

**1. Anomalias (WoW)**
Calcula el cambio porcentual entre la semana actual y la anterior: `pct_change = (L0W_ROLL - L1W_ROLL) / |L1W_ROLL|`. Filtra filas donde `|pct_change| > 0.10`. Clasifica como deterioro o mejora segun la polaridad de la metrica (para "Restaurants Markdowns / GMV" la polaridad es inversa: un aumento es deterioro).

**2. Tendencias negativas**
Recorre las 9 semanas de derecha a izquierda (L0W hacia L8W) contando declives consecutivos donde `valor[w] < valor[w-1]`. Emite un hallazgo si hay 3 o mas semanas consecutivas de caida. La severidad combina cantidad de semanas y porcentaje de caida total: `severity = weeks_declining * |total_decline_pct|`.

**3. Benchmark (outliers por grupo de pares)**
Agrupa las zonas por `(COUNTRY, ZONE_TYPE, METRIC)`. Para cada grupo con 3+ zonas, calcula media y desviacion estandar de `L0W_ROLL`. Marca las zonas cuyo valor esta por debajo de `media - 1*std`. El z-score se usa como severidad.

**4. Correlaciones entre metricas**
Para cada zona, construye una matriz de metricas x semanas (13 metricas x 9 semanas). Calcula la correlacion de Pearson entre cada par de metricas usando `numpy.corrcoef`. Reporta pares donde `|r| > 0.7`, requiriendo al menos 4 puntos validos y descartando series constantes.

### Orquestacion y reporte

`run_all_detectors` ejecuta los 4 detectores, une los hallazgos y los ordena por severidad descendente. Los top 5 se envian junto con un resumen por categoria a GPT-4.1-mini, que genera el reporte ejecutivo en Markdown. La respuesta del endpoint incluye el Markdown (`report_md`) y datos estructurados (`chart_data`) para graficar en el frontend con Chart.js.

## Como Utilizarlo

1. Abre la interfaz web en tu navegador.
2. Escribe preguntas relacionadas con los datos operacionales de Rappi (ej: "¿Cuál fue el promedio de órdenes el lunes pasado?" o "¿Qué tienda tuvo más anomalías en las métricas?").
3. El agente procesará la información, ejecutará el código necesario sobre los DataFrames y te devolverá una respuesta estructurada.

## Costos Estimados

El costo por pregunta de la solución depende de la complejidad de la consulta (cuántos pasos de razonamiento requiera el agente), pero en promedio se estima:

- **Entrada:** Entre 1000 y 2000 tokens.
- **Salida:** Entre 150 y 300 tokens.

Por lo que para 10 preguntas nos da un costo aproximado de 0.011 - 0.015 dolares.

*Nota: Estos valores pueden variar según el tamaño del historial de la conversación y la cantidad de columnas en los datos analizados.*
