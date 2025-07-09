from dataclasses import replace
from logging import getLogger

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig

from ..config import load_prompt
from ..models import ChatState

log = getLogger(__name__)

__all__ = ["rewriter_factory"]

_REWRITE_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", load_prompt("rewrite")),
        ("human", "# Question\n\n{question}"),
    ]
)


def rewriter_factory(llm):
    async def rewriter_node(state: ChatState, config: RunnableConfig) -> ChatState:
        log.debug("Entering rewrite node")
        prompt = _REWRITE_PROMPT.format_messages(question=state.question())

        response = await llm.ainvoke(prompt)
        search_query = response.content.strip()
        log.info("Question rewritten as query: %s", search_query)

        return replace(state, search_query=search_query)

    return rewriter_node
