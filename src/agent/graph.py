from langchain_openai import ChatOpenAI
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
import pandas as pd
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.base import BaseCheckpointSaver
from .prompts import PANDAS_AGENT_PROMPT
from langchain_core.messages import HumanMessage, AIMessage

MAX_HISTORY_EXCHANGES = 8


class AgentState(MessagesState):
    pass


class ChatGraph:
    def __init__(
        self,
        df_metrics: pd.DataFrame,
        df_orders: pd.DataFrame,
        checkpointer: BaseCheckpointSaver | None = None,
    ):
        self.pandas_model = ChatOpenAI(model="gpt-4.1-mini", temperature=0)
        self.df_metrics = df_metrics
        self.df_orders = df_orders
        self.checkpointer = checkpointer
        self.graph = self._build_graph()

    def pandas_agent(self, state: AgentState):
        """Agente que responde a la consulta del usuario usando ambos DataFrames."""
        agent = create_pandas_dataframe_agent(
            llm=self.pandas_model,
            df=[self.df_metrics, self.df_orders],
            agent_type="tool-calling",
            verbose=True,
            allow_dangerous_code=True,
        )
        messages = state["messages"]
        question = self._latest_human(state).content
        history = self._build_conversation_context(messages[:-1])

        if history:
            full_query = f"{history}\n\nNueva pregunta del usuario:\n{question}"
        else:
            full_query = question

        prompt = PANDAS_AGENT_PROMPT.format(query=full_query)
        response = agent.invoke(prompt)
        output = response["output"]
        if isinstance(output, list):
            output = "\n".join(
                block["text"] for block in output if block.get("type") == "text"
            )
        return {"messages": [AIMessage(content=output)]}

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("pandas_agent", self.pandas_agent)

        workflow.add_edge(START, "pandas_agent")
        workflow.add_edge("pandas_agent", END)

        return workflow.compile(checkpointer=self.checkpointer)

    def _build_conversation_context(self, messages: list) -> str:
        """Formatea los últimos intercambios como contexto conversacional."""
        if not messages:
            return ""

        pairs = []
        for msg in messages:
            if msg.type == "human":
                pairs.append(f"Usuario: {msg.content}")
            elif msg.type == "ai":
                content = msg.content
                if len(content) > 500:
                    content = content[:500] + "..."
                pairs.append(f"Asistente: {content}")

        # Limitar a los últimos N intercambios (2 mensajes por intercambio)
        pairs = pairs[-(MAX_HISTORY_EXCHANGES * 2) :]

        return (
            "--- Historial de conversación ---\n"
            + "\n".join(pairs)
            + "\n--- Fin del historial ---"
        )

    def _latest_human(self, state: AgentState) -> HumanMessage:
        for msg in reversed(state["messages"]):
            if msg.type == "human":
                return msg
        raise ValueError("No human message found")
