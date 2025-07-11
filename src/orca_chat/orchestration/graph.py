from langchain_core.runnables import Runnable
from langgraph.graph import END, START, StateGraph

from ..models import LLMRegistry
from ..session.chat_state import ChatState
from ..skills.generators import (
    chat_factory,
    reranker_factory,
    router_factory,
    searchifier_factory,
)
from ..skills.retrievers import wikipedia_factory


def build_chat_graph() -> Runnable:
    registry = LLMRegistry()
    g: StateGraph = StateGraph(ChatState)

    # -- Generators --
    g.add_node("router", router_factory(registry.get("router")))
    g.add_node("searchifier", searchifier_factory(registry.get("searchifier")))
    g.add_node("reranker", reranker_factory(registry.get("reranker")))
    g.add_node("chat", chat_factory(registry.get("chat")))

    # -- Retrievers --
    g.add_node("wikipedia", wikipedia_factory())

    # -- Graph Edges --
    g.add_edge(START, "router")
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
    g.add_edge("wikipedia", "reranker")
    g.add_edge("reranker", "chat")
    g.add_edge("chat", END)

    return g.compile()
