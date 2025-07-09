from langchain_core.runnables import Runnable
from langgraph.graph import END, START, StateGraph

from ..config import load_config
from ..models import ChatState, LLMRegistry
from ..skills import (
    chat_factory,
    reranker_factory,
    retriever_factory,
    rewriter_factory,
    router_factory,
)
from ..skills.retrievers import wiki_factory

__all__ = ["build_chat_graph"]


def build_chat_graph() -> Runnable:
    model_cfg = load_config("models")
    registry = LLMRegistry.from_dict(model_cfg)

    llm = registry.get("llama3")
    wiki_retriever = wiki_factory()

    router_node = router_factory(llm)
    rewriter_node = rewriter_factory(llm)
    retriever_node = retriever_factory(wiki_retriever)
    reranker_node = reranker_factory(llm)
    chat_node = chat_factory(llm)

    g: StateGraph = StateGraph(ChatState)

    g.add_node("route", router_node)
    g.add_node("rewrite", rewriter_node)
    g.add_node("retrieve", retriever_node)
    g.add_node("rerank", reranker_node)
    g.add_node("chat", chat_node)

    g.add_edge(START, "route")
    g.add_conditional_edges(
        "route",
        lambda state: state.router_flags,
        {
            "wiki": "rewrite",
            "direct": "chat",
        },
    )
    g.add_edge("rewrite", "retrieve")
    g.add_edge("retrieve", "rerank")
    g.add_edge("rerank", "chat")
    g.add_edge("chat", END)

    return g.compile()
