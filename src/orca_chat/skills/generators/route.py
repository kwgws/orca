from dataclasses import replace
from logging import getLogger

import regex as re
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langgraph.graph.state import StateNode

from ...session import ChatState

log = getLogger(__name__)
_re_choice = re.compile(r"[^a-z]+")

_INSTRUCTIONS = """
You are a router. Your task is to direct the user's message to the correct
destination. Carefully read the user's message, then respond using only one
of these two words:

- "none," if there is _no_ question, or if there is a question that:
    - is straightforward, simple, or direct,
    - refers explicitly to earlier parts of the conversation,
    - or can be answered using general knowledge.

- "wiki," if there _is_ a question, and the question:
    - relates to current events,
    - involves detailed scholarly information,
    - asks about specific people, historical details, or precise data,
    - or is likely best answered by consulting Wikipedia.
    
If context, chat summary, and/or chat history are provided, use them to help
make your decision. Otherwise ignore those fields.

### EXAMPLES ###
- Q: "Hello!" A: none
- Q: "Tell me about yourself." A: none
- Q: "Explain the history of the U.S. Supreme Court." A: wiki
- Q: "Rewrite these instructions as bullet points." A: none
- Q: "Why does the sun set in the west?" A: none
- Q: "What made 'The Little Mermaid' a successful film?" A: wiki

**Reminder**: respond _only_ with either "wiki" or "none." Do not include
any punctuation. Do not provide explanations or additional context.
"""

_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", "## INSTRUCTIONS ##\n{instructions}"),
        ("system", "## CONTEXT ##\n{context}"),
        ("system", "## SUMMARY ##\n{summary}"),
        MessagesPlaceholder("chat_history"),
        ("human", "{question}"),
    ]
)


def router_factory(llm: ChatOllama) -> StateNode:
    async def route(state: ChatState, config: RunnableConfig) -> ChatState:
        log.info("Entering router node")
        if not (state.disambiguation or state.question):
            raise ValueError("Router node called but no question provided")

        prompt = _PROMPT.format_messages(
            instructions=_INSTRUCTIONS,
            context=state.get_documents_str() or "N/A",
            summary=state.summary or "N/A",
            chat_history=state.chat_history,
            question=state.disambiguation or state.question,
        )
        response = await llm.ainvoke(prompt)

        choice = _re_choice.sub("", str(response.content))
        if "wiki" in choice:
            log.info("Router sending query to Wikipedia node")
        else:
            log.info("Router sending query to chat node")
            choice = "none"
        return replace(
            state,
            router_flags=choice,
        )

    return route
