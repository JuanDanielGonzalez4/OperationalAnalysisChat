import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from src.config import settings  # noqa: F401 — loads .env into os.environ
from src.agent.graph import ChatGraph
from src.api.chat import router as chat_router
from src.api.dependencies import init_chat_graph, init_dataframes, init_session_store
from src.data.loader import load_dataframes
from src.services.session_store import SessionStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    df_metrics, df_orders = load_dataframes()
    init_dataframes(df_metrics, df_orders)

    async with AsyncSqliteSaver.from_conn_string("data/sessions.db") as checkpointer:
        chat_graph = ChatGraph(df_metrics, df_orders, checkpointer=checkpointer)
        init_chat_graph(chat_graph)
        logger.info("ChatGraph inicializado con checkpointer SQLite")

        session_store = SessionStore(db_path="data/sessions.db")
        await session_store.init_db()
        init_session_store(session_store)
        logger.info("SessionStore inicializado")

        yield


app = FastAPI(title="Chat Operation Analysis", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api")

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def serve_index():
    return FileResponse("static/index.html")


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
