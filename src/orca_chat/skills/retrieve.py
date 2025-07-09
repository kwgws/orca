from dataclasses import replace
from logging import getLogger

from langchain_core.runnables import RunnableConfig

from ..models import ChatState

log = getLogger(__name__)

__all__ = ["retriever_factory"]


def retriever_factory(retriever):
    async def retriever_node(state: ChatState, config: RunnableConfig) -> ChatState:
        log.debug("Entering retriever node")

        docs = retriever.invoke(state.search_query)
        if len(docs) < 1:
            log.warning("No documents retrieved")
        for doc in docs:
            log.info("Retrieved document: %s", doc.metadata.get("source"))

        return replace(state, documents=docs)

    return retriever_node
