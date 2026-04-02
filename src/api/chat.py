import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from src.agent.graph import ChatGraph
from src.api.dependencies import (
    get_cached_insights,
    get_chat_graph,
    get_dataframes,
    get_session_store,
    set_cached_insights,
)
from src.services.session_store import SessionStore

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)


class MessageBody(BaseModel):
    message: str
    session_id: str | None = Field(
        default=None,
        description="ID de sesión para continuidad de conversación",
    )


class ChatResponse(BaseModel):
    answer: str
    session_id: str


class SessionOut(BaseModel):
    session_id: str
    title: str
    created_at: str
    last_active: str


class MessageOut(BaseModel):
    role: str
    content: str


class HistoryResponse(BaseModel):
    session_id: str
    messages: list[MessageOut]


@router.post("/message", response_model=ChatResponse)
async def send_message(
    dto: MessageBody,
    chat_graph: ChatGraph = Depends(get_chat_graph),
    session_store: SessionStore = Depends(get_session_store),
):
    """Envía un mensaje al agente de análisis y retorna la respuesta."""
    session_id = dto.session_id or str(uuid.uuid4())

    await session_store.get_or_create(session_id, dto.message)

    result = await chat_graph.graph.ainvoke(
        {"messages": [HumanMessage(content=dto.message)]},
        config={"configurable": {"thread_id": session_id}},
    )

    final_message = result["messages"][-1]

    return ChatResponse(
        answer=final_message.content,
        session_id=session_id,
    )


@router.get("/history", response_model=HistoryResponse)
async def get_history(
    session_id: str,
    chat_graph: ChatGraph = Depends(get_chat_graph),
    session_store: SessionStore = Depends(get_session_store),
):
    """Retorna el historial de conversación de una sesión."""
    session = await session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    config = {"configurable": {"thread_id": session_id}}
    state = await chat_graph.graph.aget_state(config)

    if not state or not state.values:
        return HistoryResponse(session_id=session_id, messages=[])

    messages = [
        MessageOut(
            role="user" if m.type == "human" else "assistant",
            content=m.content,
        )
        for m in state.values["messages"]
    ]
    return HistoryResponse(session_id=session_id, messages=messages)


@router.get("/sessions", response_model=list[SessionOut])
async def list_sessions(
    session_store: SessionStore = Depends(get_session_store),
):
    """Lista todas las sesiones de chat ordenadas por actividad reciente."""
    sessions = await session_store.list_sessions()
    return [SessionOut(**s) for s in sessions]


class ChartData(BaseModel):
    anomalies: list[dict]
    trends: list[dict]
    benchmarks: list[dict]
    correlations: list[dict]


class InsightsReportResponse(BaseModel):
    report_md: str
    chart_data: ChartData


MAX_CHART_ITEMS = 15


def _build_chart_data(findings: dict) -> ChartData:
    """Extract top findings per category for frontend charts."""
    return ChartData(
        anomalies=findings["anomalies"][:MAX_CHART_ITEMS],
        trends=findings["trends"][:MAX_CHART_ITEMS],
        benchmarks=findings["benchmarks"][:MAX_CHART_ITEMS],
        correlations=findings["correlations"][:MAX_CHART_ITEMS],
    )


@router.get("/insights", response_model=InsightsReportResponse)
def get_insights():
    """Retorna el último reporte de insights cacheado."""
    cached = get_cached_insights()
    if cached is None:
        return InsightsReportResponse(
            report_md="# Insights\n\nNo hay insights generados. Haz clic en **Generar Insights**.",
            chart_data=ChartData(anomalies=[], trends=[], benchmarks=[], correlations=[]),
        )
    return InsightsReportResponse(**cached)


@router.post("/insights/generate", response_model=InsightsReportResponse)
async def generate_insights():
    """Ejecuta detectores determinísticos + narración LLM y cachea el resultado."""
    from src.services.insights_engine import run_all_detectors
    from src.services.insights_narration import generate_narrative

    df_metrics, df_orders = get_dataframes()

    # Run CPU-bound detectors in a thread to avoid blocking the event loop
    loop = asyncio.get_running_loop()
    findings = await loop.run_in_executor(None, run_all_detectors, df_metrics, df_orders)

    # LLM narration (async)
    report_md = await generate_narrative(findings)

    chart_data = _build_chart_data(findings)

    result = {"report_md": report_md, "chart_data": chart_data.model_dump()}
    set_cached_insights(result)

    return InsightsReportResponse(report_md=report_md, chart_data=chart_data)

