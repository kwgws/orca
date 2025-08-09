# orca_chat/skills/route.py

from textwrap import dedent
from typing import Any, Final

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import StateNode

from ..llm import get_llm
from ..state import ConversationState, get_history

__all__: Final = ["route_node"]


def route_node(**llm_kwargs) -> StateNode:
    """..."""
    prompt = dedent(f"""
    {{input}}
    
    {"-" * 20}
    
    Decide whether this request should be answered directly (“chat”)
    or by calling one of our tools (“tools”).

    Available tool(s):
    - wikipedia_search — Search Wikipedia for background facts, dates, and short
      summaries about people, places, events, or concepts. Input is a concise
      search query.

    Choose “tools” when the user:
    - asks to “look up”, “search”, “check Wikipedia”, or explicitly requests
      factual background information;
    - asks “who/what/when is ...”, or about named entities you may not know;
    - seeks definitions, dates, biographies, places, historical events, or
      other scholarly knowledge that that Wikipedia typically covers.

    Otherwise choose “chat”.

    Do **NOT** explain or contextualize your choice.
    Respond **ONLY** one word: tools or chat.
    If you are uncertain, default to chat.
    """)

    async def _route(
        state: ConversationState, config: RunnableConfig, **_
    ) -> dict[str, Any]:
        """..."""
        llm = await get_llm(**llm_kwargs)

        history = get_history(state, include_summary=False)

        if len(history) == 1:
            messages = [HumanMessage(prompt.format(input=history[0]))]

        else:  # len(history) > 1
            last_message = history.pop()
            messages = [
                *history,
                HumanMessage(prompt.format(input=last_message)),
            ]

        reply = await llm.ainvoke(messages, config=config)
        return {"payload": {"route": str(reply.content)}}

    return _route
