import logging
import uuid
import os

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from src.agent.graph import ChatGraph
from src.api.dependencies import get_chat_graph, get_session_store
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


class InsightsResponse(BaseModel):
    content: str


@router.get("/insights", response_model=InsightsResponse)
def get_insights():
    """Retorna el contenido del archivo de insights si existe."""
    filepath = "data/insights.md"
    if not os.path.exists(filepath):
        return InsightsResponse(content="# Insights\n\nNo hay insights generados. Haz clic en 'Generar Insights'.")
    
    with open(filepath, mode="r", encoding="utf-8") as f:
        content = f.read()
        return InsightsResponse(content=content)


@router.post("/insights/generate", response_model=InsightsResponse)
async def generate_insights(
    chat_graph: ChatGraph = Depends(get_chat_graph),
    session_store: SessionStore = Depends(get_session_store),
):
    """Genera nuevos insights usando el agente y los guarda en insights.md"""
    session_id = "insights_generation_session"
    prompt = "Genera un reporte DETALLADO de insights operativos, estrategias de precios y recomendaciones para Rappi basado en los datos actuales. Formatea el resultado en Markdown profesional con títulos, listas, y texto en negrita. Analiza profundamente el performance y da recomendaciones accionables."
    
    await session_store.get_or_create(session_id, "Generación de Insights")
    
    result = await chat_graph.graph.ainvoke(
        {"messages": [HumanMessage(content=prompt)]},
        config={"configurable": {"thread_id": session_id}},
    )
    
    final_message = result["messages"][-1].content
    
    filepath = "data/insights.md"
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, mode="w", encoding="utf-8") as f:
        f.write(final_message)
        
    return InsightsResponse(content=final_message)

