# Rappi AI Analyst — Sistema de Análisis Inteligente para Operaciones

## Project Overview

An AI-powered system for Rappi's SP&A and Operations teams that enables non-technical users to query operational metrics via natural language and auto-generates executive insight reports. Two core deliverables: a **conversational data bot** (70% weight) and an **automated insights engine** (30% weight).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND (React/Next.js)                │
│  - Chat interface with message history                      │
│  - Plotly chart rendering (via JSON from API)                │
│  - Insight report viewer                                    │
│  - Suggested follow-up questions (clickable)                │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP (JSON)
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                     BACKEND (FastAPI)                        │
│                                                             │
│  POST /api/chat          → Chatbot endpoint                 │
│  GET  /api/chat/history  → Retrieve conversation history    │
│  POST /api/insights      → Trigger insight generation       │
│  GET  /api/insights/report → Get latest generated report    │
│  GET  /api/schema        → Return dataset schema + metrics  │
│  GET  /api/health        → Healthcheck                      │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              AGENT LAYER (LangChain)                │    │
│  │                                                     │    │
│  │  ┌─────────────┐    ┌──────────────────────────┐    │    │
│  │  │  System     │    │  LangChain Pandas        │    │    │
│  │  │  Prompt     │───▶│  DataFrame Agent         │    │    │
│  │  │  Builder    │    │  (text-to-code)           │    │    │
│  │  └─────────────┘    └──────────┬───────────────┘    │    │
│  │                                │                    │    │
│  │                     ┌──────────▼───────────────┐    │    │
│  │                     │  Code Executor           │    │    │
│  │                     │  (sandboxed Pandas)      │    │    │
│  │                     └──────────┬───────────────┘    │    │
│  │                                │                    │    │
│  │                     ┌──────────▼───────────────┐    │    │
│  │                     │  Response Formatter      │    │    │
│  │                     │  + Chart Generator       │    │    │
│  │                     └──────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │           INSIGHTS ENGINE (Python + LLM)            │    │
│  │                                                     │    │
│  │  Anomaly Detector → Trend Analyzer → Benchmarker    │    │
│  │  → Correlation Finder → LLM Report Narrator         │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              DATA LAYER (Pandas)                    │    │
│  │                                                     │    │
│  │  df_metrics: Métricas Input (wide format, L8W-L0W)  │    │
│  │  df_orders:  Órdenes por zona (wide format, L8W-L0W)│    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer    | Technology                                        | Why                                                   |
| -------- | ------------------------------------------------- | ----------------------------------------------------- |
| LLM      | Claude Sonnet (Anthropic)                         | Strong code generation, good instruction following    |
| Agent    | LangChain `create_pandas_dataframe_agent`       | Purpose-built for text-to-Pandas-code over DataFrames |
| Backend  | FastAPI                                           | Async, fast, auto-generated OpenAPI docs              |
| Frontend | React or Next.js (separate repo or `/frontend`) | Decoupled from backend, developer's choice            |
| Charts   | Plotly                                            | Interactive, JSON-serializable for API transport      |
| Reports  | Markdown → PDF (weasyprint)                      | Clean executive reports, exportable                   |
| Data     | Pandas DataFrames (in-memory)                     | Datasets are small enough, no DB needed               |

---

## Project Structure

```
rappi-ai-analyst/
├── README.md
├── requirements.txt
├── .env.example                    # API keys template
├── .env                            # (gitignored) actual keys
│
├── data/
│   ├── metrics_input.csv           # Dataset 1: operational metrics by zone
│   └── orders.csv                  # Dataset 2: order volumes by zone
│
├── src/
│   ├── __init__.py
│   ├── config.py                   # Settings via pydantic-settings (env vars)
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   ├── loader.py               # Load CSVs into DataFrames at startup
│   │   ├── schema.py               # Metric dictionary + column descriptions
│   │   └── preprocessor.py         # Cleaning, type casting, derived columns
│   │
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── prompts.py              # System prompt builder with full business context
│   │   ├── pandas_agent.py         # LangChain Pandas DataFrame Agent setup
│   │   ├── memory.py               # ConversationBufferWindowMemory (last 8 turns)
│   │   └── charts.py               # Plotly chart generation from query results
│   │
│   ├── insights/
│   │   ├── __init__.py
│   │   ├── anomaly_detector.py     # WoW changes > 10% (deterioration/improvement)
│   │   ├── trend_analyzer.py       # 3+ consecutive weeks of decline
│   │   ├── benchmarker.py          # Same country/type zones with divergent performance
│   │   ├── correlations.py         # Cross-metric correlation analysis
│   │   └── report_generator.py     # Structured findings → LLM narration → MD/PDF
│   │
│   └── api/
│       ├── __init__.py
│       ├── main.py                 # FastAPI app factory, CORS, lifespan
│       ├── routes/
│       │   ├── __init__.py
│       │   ├── chat.py             # POST /api/chat, GET /api/chat/history
│       │   ├── insights.py         # POST /api/insights, GET /api/insights/report
│       │   └── schema.py           # GET /api/schema
│       ├── models.py               # Pydantic request/response schemas
│       └── dependencies.py         # Shared deps (dataframes, agent instance)
│
├── tests/
│   ├── test_agent.py               # Agent responds correctly to sample queries
│   ├── test_insights.py            # Insight detection logic unit tests
│   └── test_api.py                 # Endpoint integration tests
│
└── notebooks/
    └── eda.ipynb                   # Initial data exploration (for presentation)
```

---

## API Specification

### `POST /api/chat`

Conversational endpoint. Receives a user question, runs the LangChain Pandas agent, returns a natural language answer with optional chart data.

```jsonc
// Request
{
  "message": "¿Cuáles son las 5 zonas con mayor Lead Penetration esta semana?",
  "session_id": "uuid-optional"  // for memory continuity
}

// Response
{
  "answer": "Las 5 zonas con mayor Lead Penetration en la semana actual (L0W) son: ...",
  "chart": {                      // null if no chart needed
    "type": "bar",
    "plotly_json": { ... }        // Plotly figure as JSON (fig.to_json())
  },
  "code_executed": "df_metrics[df_metrics['METRIC'] == 'Lead Penetration'].nlargest(5, 'L0W_VALUE')",
  "suggested_questions": [
    "¿Cómo ha evolucionado el Lead Penetration en estas zonas en las últimas 8 semanas?",
    "¿Cuáles son las zonas con menor Lead Penetration?"
  ],
  "session_id": "uuid"
}
```

### `GET /api/chat/history?session_id=uuid`

```jsonc
// Response
{
  "session_id": "uuid",
  "messages": [
    { "role": "user", "content": "...", "timestamp": "..." },
    { "role": "assistant", "content": "...", "chart": null, "timestamp": "..." }
  ]
}
```

### `POST /api/insights`

Triggers full automated analysis. Can be slow (30-60s), consider background task.

```jsonc
// Request
{
  "format": "markdown"  // "markdown" | "html" | "pdf"
}

// Response
{
  "status": "completed",
  "report": {
    "executive_summary": "...",
    "anomalies": [ { "zone": "...", "metric": "...", "change_pct": -15.2, "detail": "..." } ],
    "trends": [ { "zone": "...", "metric": "...", "weeks_declining": 4, "detail": "..." } ],
    "benchmarks": [ { "zones_compared": [...], "finding": "..." } ],
    "correlations": [ { "metrics": ["...", "..."], "correlation": 0.87, "detail": "..." } ],
    "recommendations": [ "..." ]
  },
  "report_rendered": "# Executive Report\n\n## Top Findings\n..."  // full markdown
}
```

### `GET /api/insights/report`

Returns the latest generated report (cached).

### `GET /api/schema`

Returns dataset metadata for the frontend to display context.

```jsonc
// Response
{
  "datasets": {
    "metrics": {
      "columns": ["COUNTRY", "CITY", "ZONE", "ZONE_TYPE", "ZONE_PRIORITIZATION", "METRIC", "L8W_VALUE", ..., "L0W_VALUE"],
      "row_count": 12345,
      "countries": ["AR", "BR", "CL", "CO", "CR", "EC", "MX", "PE", "UY"],
      "metrics_available": ["Lead Penetration", "Perfect Orders", ...]
    },
    "orders": {
      "columns": ["COUNTRY", "CITY", "ZONE", "METRIC", "L8W", ..., "L0W"],
      "row_count": 6789
    }
  },
  "metric_dictionary": {
    "Lead Penetration": "Tiendas habilitadas en Rappi / (leads + habilitadas + salieron)",
    "Perfect Orders": "Órdenes sin cancelaciones, defectos o demora / Total órdenes",
    ...
  }
}
```

---

## Data Context (Critical for Agent Prompts)

The system prompt MUST include this context so the LLM generates correct Pandas code.

### Dataset 1: `metrics_input.csv`

Operational metrics per zone, with 9 weekly columns (L8W through L0W where L0W = current week, L8W = 8 weeks ago).

| Column                 | Type   | Description                                         |
| ---------------------- | ------ | --------------------------------------------------- |
| COUNTRY                | string | Country code: AR, BR, CL, CO, CR, EC, MX, PE, UY    |
| CITY                   | string | City name                                           |
| ZONE                   | string | Operational zone / neighborhood                     |
| ZONE_TYPE              | string | "Wealthy" or "Non Wealthy"                          |
| ZONE_PRIORITIZATION    | string | "High Priority" / "Prioritized" / "Not Prioritized" |
| METRIC                 | string | Metric name (see dictionary below)                  |
| L8W_VALUE … L0W_VALUE | float  | Metric value for each of the last 9 weeks           |

### Dataset 2: `orders.csv`

Order volumes per zone with same weekly structure.

| Column              | Type   | Description            |
| ------------------- | ------ | ---------------------- |
| COUNTRY, CITY, ZONE | string | Geographic identifiers |
| METRIC              | string | Always "Orders"        |
| L8W … L0W          | float  | Order count per week   |

### Metric Dictionary

Include this VERBATIM in the system prompt so the agent understands business meaning:

| Metric                                         | Description                                                                           |
| ---------------------------------------------- | ------------------------------------------------------------------------------------- |
| % PRO Users Who Breakeven                      | Pro subscription users whose generated value covers membership cost / Total Pro users |
| % Restaurants Sessions With Optimal Assortment | Sessions with minimum 40 restaurants available / Total sessions                       |
| Gross Profit UE                                | Gross profit margin / Total orders                                                    |
| Lead Penetration                               | Enabled stores / (leads + enabled + churned stores)                                   |
| MLTV Top Verticals Adoption                    | Users ordering across multiple verticals / Total users                                |
| Non-Pro PTC > OP                               | Non-Pro conversion from "Proceed to Checkout" to "Order Placed"                       |
| Perfect Orders                                 | Orders without cancellations, defects, or delays / Total orders                       |
| Pro Adoption                                   | Pro subscription users / Total Rappi users                                            |
| Restaurants Markdowns / GMV                    | Restaurant discounts / Restaurant Gross Merchandise Value                             |
| Restaurants SS > ATC CVR                       | Restaurant "Select Store" to "Add to Cart" conversion                                 |
| Restaurants SST > SS CVR                       | Restaurant vertical selection to specific store selection conversion                  |
| Retail SST > SS CVR                            | Retail vertical selection to specific store selection conversion                      |
| Turbo Adoption                                 | Turbo (fast delivery) users / Total users with Turbo available                        |

---

## Chatbot Behavior Spec

### Required Query Types (all must work)

1. **Filtering** : "¿Cuáles son las 5 zonas con mayor % Lead Penetration esta semana?"
2. **Comparisons** : "Compara el Perfect Order entre zonas Wealthy y Non Wealthy en México"
3. **Temporal trends** : "Muestra la evolución de Gross Profit UE en Chapinero últimas 8 semanas"
4. **Aggregations** : "¿Cuál es el promedio de Lead Penetration por país?"
5. **Multivariate** : "¿Qué zonas tienen alto Lead Penetration pero bajo Perfect Order?"
6. **Inference** : "¿Cuáles son las zonas que más crecen en órdenes en las últimas 5 semanas y qué podría explicar el crecimiento?"

### Agent Behavior

* **Business context awareness** : If user asks about "zonas problemáticas" → infer zones with deteriorating metrics
* **Proactive suggestions** : After each answer, suggest 2-3 relevant follow-up questions
* **Conversational memory** : Track last 8 turns, resolve references like "y en México?" or "ahora compara con la semana pasada"
* **Chart generation** : When the question involves trends → line chart. Comparisons → bar chart. Return Plotly JSON in the response.
* **Error recovery** : If generated Pandas code fails, capture the error, send it back to the LLM for a retry (max 2 retries)
* **Language** : Respond in Spanish (the users are Rappi LATAM operations teams)

---

## Insights Engine Spec

### Detection Rules (deterministic Python, NOT LLM-driven)

| Category               | Logic                                                                                                               |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------- |
| **Anomalies**    | Any zone where `abs((L0W - L1W) / L1W) > 0.10`— flag as anomaly. Separate into deterioration vs improvement.     |
| **Trends**       | Any zone+metric where values have decreased for 3+ consecutive weeks (L0W < L1W < L2W < L3W).                       |
| **Benchmarking** | Group zones by (COUNTRY, ZONE_TYPE). For each metric, find zones performing >1 std dev below their peer group mean. |
| **Correlations** | For each zone, compute Pearson correlation between all metric pairs across 9 weeks. Flag pairs with                 |

### Report Generation Flow

1. Run all 4 detectors → collect structured findings (Python dicts/dataclasses)
2. Rank findings by severity/impact (anomalies with largest % change first)
3. Select top 3-5 critical findings for executive summary
4. Send structured findings to LLM with prompt: "Generate an executive report in Spanish for Rappi operations leadership. Be concise and actionable."
5. Output as Markdown (primary), with optional PDF export

---

## Environment Setup

```bash
# Clone and setup
git clone <repo-url>
cd rappi-ai-analyst
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your API key:
#   ANTHROPIC_API_KEY=sk-ant-...
#   or OPENAI_API_KEY=sk-...

# Run
uvicorn src.api.main:app --reload --port 8000

# API docs available at http://localhost:8000/docs
```

### Required Dependencies

```
fastapi>=0.110
uvicorn[standard]>=0.27
langchain>=0.3
langchain-anthropic>=0.3       # or langchain-openai
pandas>=2.2
plotly>=5.20
pydantic>=2.6
pydantic-settings>=2.2
python-dotenv>=1.0
weasyprint>=62                  # for PDF export (optional)
pytest>=8.0
httpx>=0.27                     # for async test client
```

---
