import json
from dataclasses import replace
from logging import getLogger

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langgraph.graph.state import StateNode

from ...session import ChatState

log = getLogger(__name__)

_RERANKER_IN_MAX_DOCS = 10
_RERANKER_IN_MAX_CHARS = 300
_RERANKER_OUT_MAX_DOCS = 3

_INSTRUCTIONS = """
Give each of the following documents a score between 0 and 10 according to how
direclty relevant and useful they would be in answering the question below.
Reply with a JSON-formatted array of [[index, score], ...].
Do _not_ explain your reasoning or include any other context. Respond _only_
with a single JSON string.
**THIS IS IMPORTANT**. Your raw reply is going _directly_ into a JSON parser.
**Do _NOT_ include _ANY_ text other than the JSON itself**!!!
"""

_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", "## INSTRUCTIONS ##\n{instructions}"),
        ("system", "## DOCUMENTS ##\n{context}"),
        ("system", "## SUMMARY ##\n{summary}"),
        MessagesPlaceholder("chat_history"),
        ("human", "{query}"),
    ]
)


def reranker_factory(llm: ChatOllama) -> StateNode:
    async def rerank(state: ChatState, config: RunnableConfig) -> ChatState:
        log.info("Entering reranker node")
        if not (state.search_query):
            raise ValueError("Reranker called but no search query provided")
        if not state.documents:
            raise ValueError("Reranker called but no documents provided")

        prompt = _PROMPT.format_messages(
            instructions=_INSTRUCTIONS,
            context=state.get_documents_str(
                max_chars=_RERANKER_IN_MAX_CHARS, max_documents=_RERANKER_IN_MAX_DOCS
            ),
            summary=state.summary or "N/A",
            chat_history=state.chat_history,
            query=state.search_query,
        )
        response = await llm.ainvoke(prompt)
        json_str = response.text().strip()

        try:
            data = json.loads(json_str)
            norm = [[int(x) for x in pair] for pair in data][:_RERANKER_OUT_MAX_DOCS]
            rank = sorted(norm, key=lambda doc: doc[0])
            docs = [state.documents[i] for i, score in rank if score > 2]
        except Exception as e:
            log.warning("Error during JSON handling: %s", e)
            docs = state.documents

        for i, doc in enumerate(docs):
            log.info("Result %d: %s", i, doc.metadata.get("source") or "unknown")
        return replace(
            state,
            documents=docs,
        )

    return rerank
