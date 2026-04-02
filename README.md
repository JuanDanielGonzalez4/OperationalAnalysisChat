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

## Cómo Utilizarlo

1. Abre la interfaz web en tu navegador.
2. Escribe preguntas relacionadas con los datos operacionales de Rappi (ej: "¿Cuál fue el promedio de órdenes el lunes pasado?" o "¿Qué tienda tuvo más anomalías en las métricas?").
3. El agente procesará la información, ejecutará el código necesario sobre los DataFrames y te devolverá una respuesta estructurada.

## Costos Estimados

El costo por pregunta de la solución depende de la complejidad de la consulta (cuántos pasos de razonamiento requiera el agente), pero en promedio se estima:

- **Entrada:** Entre 1000 y 2000 tokens.
- **Salida:** Entre 150 y 300 tokens.

Por lo que para 10 preguntas nos da un costo aproximado de 0.011 - 0.015 dolares.

*Nota: Estos valores pueden variar según el tamaño del historial de la conversación y la cantidad de columnas en los datos analizados.*
