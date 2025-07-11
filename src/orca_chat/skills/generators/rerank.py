import json
from dataclasses import replace
from logging import getLogger

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langgraph.graph.state import StateNode

from ...session import ChatState

log = getLogger(__name__)

_MAX_RESULTS = 3


_BASE_INSTRUCTIONS = """
You are a researcher. Your job is to consider the following list of documents
and score them, giving them a number from 0 to 5 according to how relevant and
helpful they would be in answering the question below.

Reply with a JSON-formatted array of [[index, score], ...] with the highest
score listed first.

## DOCUMENTS ##
{documents}

**IMPORTANT:** Do _not_ explain your reasoning or include any other context.
Respond _only_ with a properly-formatted JSON string.
"""

_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _BASE_INSTRUCTIONS),
        ("human", "{question}"),
    ]
)


def reranker_factory(llm: ChatOllama) -> StateNode:
    async def rerank(state: ChatState, config: RunnableConfig) -> ChatState:
        log.debug("Entering rerank node")

        if not state.documents:
            raise ValueError("Reranker called but no documents provided")

        candidates = [
            f"[{i}] {doc.metadata.get('source', '[No source?]')}"
            for i, doc in enumerate(state.documents)
        ]
        prompt = _PROMPT.format_messages(documents=candidates, question=state.question)

        response = await llm.ainvoke(prompt)
        json_str = response.text().strip()

        try:
            data = json.loads(json_str)
            ranked = [state.documents[i] for i, score in data if int(score) > 2][:_MAX_RESULTS]
        except Exception as e:
            log.warning("Exception during JSON handling: %s", e)
            ranked = state.documents[:_MAX_RESULTS]

        for doc in ranked:
            log.info("Reranker picked: %s", doc.metadata.get("source", "[No source?]"))
        return replace(state, documents=ranked)

    return rerank
