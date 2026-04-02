"""LLM narration of structured insights findings."""

from langchain_openai import ChatOpenAI

NARRATION_PROMPT = """Eres un analista senior de operaciones de Rappi. Genera un reporte ejecutivo en español basado en los siguientes hallazgos determinísticos de datos.

## Estadísticas Generales
- Anomalías detectadas: {anomaly_count}
- Tendencias negativas: {trend_count}
- Zonas por debajo del benchmark: {benchmark_count}
- Correlaciones fuertes: {correlation_count}

## Hallazgos Críticos (Top 5)
{top_critical_text}

## Anomalías (Top 10)
{anomalies_text}

## Tendencias Negativas (Top 10)
{trends_text}

## Benchmark — Zonas Rezagadas (Top 10)
{benchmarks_text}

## Correlaciones Fuertes (Top 10)
{correlations_text}

---

Genera un reporte Markdown profesional con las siguientes secciones:

1. **Resumen Ejecutivo** — 3 a 5 oraciones con los hallazgos más críticos y su impacto potencial
2. **Alertas Críticas** — Los top 5 hallazgos con contexto detallado y recomendación específica para cada uno
3. **Análisis por Categoría**:
   - Anomalías: patrones principales, zonas/métricas más afectadas
   - Tendencias: métricas con deterioro persistente, riesgo si no se actúa
   - Benchmark: zonas rezagadas vs sus pares, oportunidades de mejora
   - Correlaciones: relaciones entre métricas que sugieren causas raíz
4. **Oportunidades** — Zonas o métricas con mejoras recientes que podrían replicarse
5. **Recomendaciones Accionables** — Lista priorizada de acciones concretas

Usa formato Markdown con headers, negritas y listas. El reporte debe ser accionable para directores de operaciones de Rappi. Se conciso pero específico — incluye nombres de zonas, métricas y porcentajes."""


def _format_anomaly(f: dict) -> str:
    arrow = "↓" if f["direction"] == "deterioration" else "↑"
    return (
        f"- {arrow} **{f['zone']}** ({f['country']}, {f['city']}): "
        f"*{f['metric']}* {f['direction']} {abs(f['pct_change'])*100:.1f}% WoW "
        f"({f['l1w_value']:.4f} → {f['l0w_value']:.4f})"
    )


def _format_trend(f: dict) -> str:
    return (
        f"- **{f['zone']}** ({f['country']}, {f['city']}): "
        f"*{f['metric']}* en declive {f['weeks_declining']} semanas consecutivas "
        f"({abs(f['total_decline_pct'])*100:.1f}% caída total)"
    )


def _format_benchmark(f: dict) -> str:
    return (
        f"- **{f['zone']}** ({f['country']}, {f['city']}): "
        f"*{f['metric']}* = {f['value']:.4f} vs media del grupo = {f['peer_mean']:.4f} "
        f"(z-score: {f['z_score']:.2f}, tipo: {f['zone_type']})"
    )


def _format_correlation(f: dict) -> str:
    return (
        f"- **{f['zone']}** ({f['country']}, {f['city']}): "
        f"*{f['metric_a']}* ↔ *{f['metric_b']}* — r = {f['correlation']:.3f}"
    )


def _format_finding(f: dict) -> str:
    formatters = {
        "anomaly": _format_anomaly,
        "trend": _format_trend,
        "benchmark": _format_benchmark,
        "correlation": _format_correlation,
    }
    return formatters[f["type"]](f)


async def generate_narrative(findings: dict) -> str:
    """Take structured findings dict, send to LLM, return Markdown report."""
    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.3)

    top_critical_text = "\n".join(_format_finding(f) for f in findings["top_critical"]) or "Ninguno"
    anomalies_text = "\n".join(_format_anomaly(f) for f in findings["anomalies"][:10]) or "Ninguna"
    trends_text = "\n".join(_format_trend(f) for f in findings["trends"][:10]) or "Ninguna"
    benchmarks_text = "\n".join(_format_benchmark(f) for f in findings["benchmarks"][:10]) or "Ninguno"
    correlations_text = "\n".join(_format_correlation(f) for f in findings["correlations"][:10]) or "Ninguna"

    prompt = NARRATION_PROMPT.format(
        anomaly_count=len(findings["anomalies"]),
        trend_count=len(findings["trends"]),
        benchmark_count=len(findings["benchmarks"]),
        correlation_count=len(findings["correlations"]),
        top_critical_text=top_critical_text,
        anomalies_text=anomalies_text,
        trends_text=trends_text,
        benchmarks_text=benchmarks_text,
        correlations_text=correlations_text,
    )

    response = await llm.ainvoke(prompt)
    return response.content
