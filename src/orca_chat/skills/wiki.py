"""orca_chat/skills/wikipedia.py"""

from functools import lru_cache
from logging import getLogger
from typing import Any

import regex as re
import wikipedia
from langchain_community.retrievers import WikipediaRetriever
from langchain_core.documents import Document
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import StateNode

from ..core.session import ChatSession
from ..loaders import RAGConfig, load_config

log = getLogger(__name__)
_re_words = re.compile(r"\w+")

_CONFIG = load_config()
_RELEVANCE_THRESHOLD: float = _CONFIG.rag.relevance_threshold


def build(cfg: RAGConfig, **kwargs) -> StateNode:
    async def _wiki(state: ChatSession, config: RunnableConfig) -> dict[str, Any]:
        log.info("Entering node 'wikipedia'")

        query = state.payload.get("search_query", state.get_last_message())
        retriever = _get_retriever(**cfg)
        response = await retriever.ainvoke(query)

        docs = [doc for doc in response if _is_relevant(query, doc)]
        if not docs:
            log.warning("Found 0 documents")
        else:
            log.info("Found %d documents", len(docs))

        return {"payload": {**state.payload, "documents": docs}}

    return _wiki


@lru_cache(maxsize=1)
def _get_retriever(**kwargs: Any) -> WikipediaRetriever:
    return WikipediaRetriever(
        wiki_client=wikipedia,
        **kwargs,
    )


def _is_relevant(query: str, doc: Document, *, threshold=_RELEVANCE_THRESHOLD) -> bool:
    title = doc.metadata.get("title", "") or doc.metadata.get("source", "<no title>")

    tokens = {tok.lower() for tok in _re_words.findall(query) if len(tok) > 2}
    if not tokens:
        log.info("Refused: %s", title)
        return False

    content = doc.metadata.get("summary") or doc.page_content
    hits = sum(1 for tok in tokens if tok in f"{title} {content}".strip().lower())

    if hits / len(tokens) < threshold:
        log.info("Refused: %s", title)
        return False
    log.debug("Accepted: %s", title)
    return True
