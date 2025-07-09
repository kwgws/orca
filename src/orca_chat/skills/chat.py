from dataclasses import replace
from logging import getLogger

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig

from ..config import load_prompt
from ..models import ChatState

__all__ = ["chat_factory"]

log = getLogger(__name__)

_CHAT_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", load_prompt("chat")),
        ("human", "# Question\n\n{question}"),
    ]
)


def chat_factory(llm):
    async def responder(state: ChatState, config: RunnableConfig):
        log.debug("Entering responder node")

        document_summaries = [d.metadata["summary"] for d in state.documents or []]
        context = "\n\n".join(document_summaries)

        prompt = _CHAT_PROMPT.format_messages(question=state.question(), context=context)
        reply = await llm.ainvoke(prompt)

        return replace(state, chat_history=[*state.chat_history, reply])

    return responder
