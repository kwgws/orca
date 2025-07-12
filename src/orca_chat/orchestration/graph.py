from langchain_core.runnables import Runnable
from langgraph.graph import END, START, StateGraph

from ..models import LLMRegistry
from ..session.chat_state import ChatState
from ..skills.generators import (
    chat_factory,
    disambiguator_factory,
    reranker_factory,
    router_factory,
    searchifier_factory,
    summarizer_factory,
)
from ..skills.retrievers import wikipedia_factory

_HISTORY_THRESHOLD = 4


def build_chat_graph() -> Runnable:
    registry = LLMRegistry()
    g: StateGraph = StateGraph(ChatState)

    # -- Generators --
    g.add_node("router", router_factory(registry.get("route")))
    g.add_node("searchifier", searchifier_factory(registry.get("searchify")))
    g.add_node("reranker", reranker_factory(registry.get("rerank")))
    g.add_node("disambiguator", disambiguator_factory(registry.get("disambiguate")))
    g.add_node("chat", chat_factory(registry.get("chat")))
    g.add_node("summarizer", summarizer_factory(registry.get("summarize")))

    # -- Retrievers --
    g.add_node("wikipedia", wikipedia_factory())

    # ====== GRAPH - Disambiguation =======
    g.add_conditional_edges(
        START,
        lambda state: (
            "first_msg" if len(getattr(state, "chat_history", [])) == 0 else "follow_up"
        ),
        {
            "first_msg": "router",
            "follow_up": "disambiguator",
        },
    )
    g.add_edge("disambiguator", "router")

    # ====== GRAPH - Router =======
    g.add_conditional_edges(
        "router",
        lambda state: state.router_flags,
        {
            "wiki": "searchifier",
            "none": "chat",
        },
    )

    # ====== GRAPH - Wikipedia search =======
    g.add_edge("searchifier", "wikipedia")
    g.add_conditional_edges(
        "wikipedia",
        lambda state: "has_docs" if getattr(state, "documents", None) else "no_docs",
        {
            "has_docs": "reranker",
            "no_docs": "chat",
        },
    )
    g.add_edge("reranker", "chat")

    # ====== GRAPH - Chat =======
    g.add_conditional_edges(
        "chat",
        lambda state: (
            "summarize" if len(getattr(state, "chat_history", [])) > _HISTORY_THRESHOLD else "skip"
        ),
        {
            "summarize": "summarizer",
            "skip": END,
        },
    )
    g.add_edge("summarizer", END)

    return g.compile()
