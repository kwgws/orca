# --- orca_chat/graph/node/prune.py -------------------------------------------

from textwrap import dedent
from typing import Final

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.message import REMOVE_ALL_MESSAGES, RemoveMessage
from langgraph.graph.state import StateNode

from ..state import State

__all__: Final = [
    "prune_node",
]


_INSTRUCTIONS = dedent("""
Write a brief précis summarizing the conversation so far; no more than a
paragraph. Emphasize important facts or documents discussed along with any
open questions.
""").strip()


def prune_node(
    llm: BaseChatModel, *, min_human_msgs: int, **llm_args
) -> StateNode:
    """Summarize and trim the transcript, keeping the last N human turns.

    Parameters
    ----------
    llm
        The chat model used to generate the running summary.
    min_human_msgs
        The minimum number of **human** messages to retain in the history.
        The node will preserve all messages starting from the Nth most recent
        human message through the end of the transcript. If there are fewer
        than N human messages, the full history is kept.
    **llm_args
        Extra keyword arguments forwarded to :meth:`llm.ainvoke`.

    Returns
    -------
    StateNode
        An async callable that, when executed, replaces the transcript with:
        1) a full-history summary message (named ``"summary"``), followed by
        2) the tail slice beginning at the N-th most recent human message.

    Notes
    -----
    - The summary is generated over the *entire* pre-trim history.
    - The summary is inserted as an AI message with ``name="summary"``.
    - Trimming uses ``RemoveMessage(REMOVE_ALL_MESSAGES)`` so it works with
      LangGraph's :meth:`add_messages` reducer.
    """

    async def _run(state: State, config: RunnableConfig) -> State:
        # Generate/update the rolling summary over the full history.
        prompt = [*state["messages"], HumanMessage(_INSTRUCTIONS)]
        reply = await llm.ainvoke(prompt, config=config, **llm_args)
        reply.name = "summary"

        # Find the index of the N-th most recent human message.
        msgs = state["messages"]
        idxs = [i for i, m in enumerate(msgs) if isinstance(m, HumanMessage)]

        if len(idxs) <= min_human_msgs:
            start = 0
        else:
            start = idxs[-min_human_msgs]
        tail = msgs[start:]

        # Replace transcript with the summary & tail slice.
        return {
            "messages": [
                RemoveMessage(REMOVE_ALL_MESSAGES),
                reply,
                *tail,
            ]  # type: ignore
        }

    return _run
