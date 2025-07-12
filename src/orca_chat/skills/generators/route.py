from dataclasses import replace
from logging import getLogger

import regex as re
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langgraph.graph.state import StateNode

from ...session import ChatState

log = getLogger(__name__)
_re_choice = re.compile(r"[^a-z]+")

_SYSTEM_MESSAGE = """
You are a _router_, the first step in a graph of LLM nodes. You consider a
given user input and decide where to dispatch it next.

**Output**
Respond with one and _only_ one of these words:
- `none`, if any of these is true:
    - no question was asked or implied,
    - the question is simple, direct, or concerns general knowledge/reasoning,
    - the question refers explicitly to earlier conversation content.
- `wiki`, if a question _is_ asked or implied, and it:
    - involves current events,
    - concerns detailed scholarly or historical knowledge,
    - otherwise concerns specific people, places, ideas, or things.
    
**Rules**
1. Reply _ONLY_ with `wiki` or `none`. No punctuation, no extra text.
2. When in doubt, prefer `none`.

**Examples**
- Tell me about yourself. -> none
- Talk about the history of plastic. -> wiki
- Rewrite these instructions as bullet points. -> none
- Why does the Sun set in the west? -> none
- What made The Little Mermaid such a successful film? -> wiki
- What is the square root of 2? -> none
"""

_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM_MESSAGE),
        ("human", "{question}"),
    ]
)


def router_factory(llm: ChatOllama) -> StateNode:
    async def route(state: ChatState, config: RunnableConfig) -> ChatState:
        log.info("Entering router node")
        if not (state.disambiguation or state.question):
            raise ValueError("Router node called but no question provided")

        prompt = _PROMPT.format_messages(
            question=state.disambiguation or state.question,
        )
        response = await llm.ainvoke(prompt, config=config)

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
