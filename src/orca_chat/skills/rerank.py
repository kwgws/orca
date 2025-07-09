import json
from dataclasses import replace
from logging import getLogger

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig

from ..config import load_prompt
from ..models import ChatState

log = getLogger(__name__)

__all__ = ["reranker_factory"]

_RERANK_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", load_prompt("rerank")),
        ("human", "# Question\n\n{question}"),
    ]
)


def reranker_factory(llm):
    async def reranker_node(state: ChatState, config: RunnableConfig) -> ChatState:
        log.debug("Entering reranker node")

        docs = state.documents or []
        candidates = "\n".join(f"[{i}] {d.metadata.get('source')}" for i, d in enumerate(docs))
        prompt = _RERANK_PROMPT.format_messages(candidates=candidates, question=state.question())
        response = await llm.ainvoke(prompt)
        json_str = response.content.strip()

        try:
            ranking = json.loads(json_str)
            best_docs = [docs[i] for i, score in ranking if int(score) > 2][:3]
        except Exception as e:
            best_docs = docs[:3]
            log.warning("Exception during JSON handling: %s", e)

        for doc in best_docs:
            log.info("Reranker picked: %s", doc.metadata.get("source"))

        return replace(state, documents=best_docs)

    return reranker_node
