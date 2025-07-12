"""Construction of the LangGraph workflow used by the REPL."""

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


def build_chat_graph() -> Runnable:
    """Assemble and return the chat workflow graph."""
    registry = LLMRegistry()
    g: StateGraph = StateGraph(ChatState)

    g.add_node("router", router_factory(registry.get("route")))
    g.add_node("searchifier", searchifier_factory(registry.get("searchify")))
    g.add_node("reranker", reranker_factory(registry.get("rerank")))
    g.add_node("disambiguator", disambiguator_factory(registry.get("disambiguate")))
    g.add_node("chat", chat_factory(registry.get("chat")))
    g.add_node("summarizer", summarizer_factory(registry.get("summarize")))

    g.add_node("wikipedia", wikipedia_factory())

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

    g.add_conditional_edges(
        "router",
        lambda state: state.router_flags,
        {
            "wiki": "searchifier",
            "none": "chat",
        },
    )

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

    g.add_edge("chat", "summarizer")
    g.add_edge("summarizer", END)

    return g.compile()
