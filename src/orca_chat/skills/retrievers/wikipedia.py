from dataclasses import replace
from logging import getLogger

import regex as re
import wikipedia
from langchain_community.retrievers import WikipediaRetriever
from langchain_core.documents import Document
from langchain_core.runnables import RunnableConfig

from ...session import ChatState

log = getLogger(__name__)
_re_words = re.compile(r"\w+")

_RETRIEVER_LANGUAGE = "en"
_RETRIEVER_MAX_CHARS = 4_000
_RETRIEVER_TOP_K = 20
_RETRIEVER_THRESHOLD = 0.5


def _is_relevant(query: str, doc: Document, threshold=_RETRIEVER_THRESHOLD) -> bool:
    tokens = {t.lower() for t in _re_words.findall(query) if len(t) > 2}
    if not tokens:
        log.warning("Empty document checked for relevance: %s", doc.metadata.get("source"))
        return False

    title = doc.metadata.get("title")
    content = doc.metadata.get("summary") or doc.page_content
    text = f"{title} {content}".strip().lower()
    hits = sum(1 for t in tokens if t in text)
    return hits / len(tokens) >= threshold


def wikipedia_factory():
    async def search_wikipedia(state: ChatState, config: RunnableConfig) -> ChatState:
        print("Looking something up...")
        log.debug("Entering Wikipedia retriever node")

        if not state.search_query:
            raise ValueError("No search query provided for retriever")

        retriever = WikipediaRetriever(
            wiki_client=wikipedia,
            lang=_RETRIEVER_LANGUAGE,
            doc_content_chars_max=_RETRIEVER_MAX_CHARS,
            top_k_results=_RETRIEVER_TOP_K,
        )
        response = retriever.invoke(state.search_query)

        bad_docs = [doc for doc in response if not _is_relevant(state.search_query, doc)]
        for doc in bad_docs:
            log.info("Refused: %s", doc.metadata.get("title") or doc.metadata.get("source", ""))

        docs = [doc for doc in response if doc not in bad_docs]
        if len(docs) < 1:
            log.warning("No documents retrieved")
        for doc in docs:
            log.info("Retrieved: %s", doc.metadata.get("title") or doc.metadata.get("source", ""))
        return replace(
            state,
            documents=docs,
        )

    return search_wikipedia
