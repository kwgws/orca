from dataclasses import replace
from logging import getLogger

import wikipedia
from langchain_community.retrievers import WikipediaRetriever
from langchain_core.runnables import RunnableConfig

from ...session import ChatState

log = getLogger(__name__)


_LANGUAGE = "en"
_MAX_CHAR_LENGTH = 4_000
_MAX_RESULTS = 6


def wikipedia_factory():
    async def search_wikipedia(state: ChatState, config: RunnableConfig) -> ChatState:
        log.debug("Entering Wikipedia retriever node")

        if not state.search_query:
            raise ValueError("No search query provided for retriever")

        retriever = WikipediaRetriever(
            wiki_client=wikipedia,
            lang=_LANGUAGE,
            doc_content_chars_max=_MAX_CHAR_LENGTH,
            top_k_results=_MAX_RESULTS,
        )

        docs = retriever.invoke(state.search_query)
        if len(docs) < 1:
            log.warning("No documents retrieved")
        for doc in docs:
            log.info("Retrieved document: %s", doc.metadata.get("source", "[No source?]"))

        return replace(state, documents=docs)

    return search_wikipedia
