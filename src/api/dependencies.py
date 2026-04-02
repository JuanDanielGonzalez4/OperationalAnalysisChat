from src.agent.graph import ChatGraph
from src.services.session_store import SessionStore

_chat_graph: ChatGraph | None = None
_session_store: SessionStore | None = None


def init_chat_graph(chat_graph: ChatGraph) -> None:
    global _chat_graph
    _chat_graph = chat_graph


def get_chat_graph() -> ChatGraph:
    if _chat_graph is None:
        raise RuntimeError("ChatGraph no ha sido inicializado")
    return _chat_graph


def init_session_store(store: SessionStore) -> None:
    global _session_store
    _session_store = store


def get_session_store() -> SessionStore:
    if _session_store is None:
        raise RuntimeError("SessionStore no ha sido inicializado")
    return _session_store
