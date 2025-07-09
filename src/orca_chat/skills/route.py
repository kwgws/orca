from dataclasses import replace
from logging import getLogger

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig

from ..config import load_prompt
from ..models import ChatState

log = getLogger(__name__)

__all__ = ["router_factory"]

_ROUTER_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", load_prompt("route")),
        ("human", "# Question\n\n{question}"),
    ]
)


def router_factory(llm):
    async def router(state: ChatState, config: RunnableConfig) -> ChatState:
        log.debug("Entering router node")
        prompt = _ROUTER_PROMPT.format_messages(question=state.question())

        response = await llm.ainvoke(prompt)
        choice = response.content.strip().lower()
        log.info("Router chose: %s", choice)

        return replace(state, router_flags=choice)

    return router
