# orca_chat/state.py

"""State management utilities for Orca Chat.

Provides structured state handling for conversation management, enabling
message tracking and metadata storage within the LangGraph framework.
"""

from typing import Annotated, Any, Final, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.graph.message import add_messages

__all__: Final = [
    "MAX_HUMAN_MESSAGES",
    "ConversationState",
    "create_state",
    "get_history",
    "should_summarize",
]

MAX_HUMAN_MESSAGES = 12
"""Number of most recent human turns to retain when trimming history."""


def _join_dicts(
    left: dict[str, Any] | None, right: dict[str, Any] | None
) -> dict[str, Any]:
    """Merge two dictionaries, with values from the ``right`` dictionary
    overriding those from the ``left``."""
    return {**(left or {}), **(right or {})}


class ConversationState(TypedDict):
    """Defines the conversation state structure for LangGraph execution.

    Attributes
    ----------
    messages : list[AnyMessage]
        Accumulates chat messages throughout the conversation. Managed using
        LangGraph's :func:`add_messages` reducer.
    payload : dict[str, Any]
        Arbitrary key-value storage for additional state metadata.
        Automatically merges incoming state changes with :func:`_join_dicts`.
    """

    messages: Annotated[
        list[AnyMessage], add_messages(format="langchain-openai")  # type: ignore
    ]
    payload: Annotated[dict[str, Any], _join_dicts]


def create_state() -> ConversationState:
    """Create a new, empty conversation state."""
    return {"messages": [], "payload": {}}


def get_history(
    state: ConversationState,
    max_hum_msgs: int | None = None,
    include_summary=True,
) -> list[AnyMessage]:
    """Return a trimmed chat history, optionally prefixed with a summary.

    The history includes at most ``max_hum_msgs`` most-recent human turns,
    plus all messages after the first retained human message. If
    ``state['payload']['summary']`` is present, it is prepended as a tagged
    :class:`AIMessage`.

    Parameters
    ----------
    state
        The current conversation state.
    max_hum_msgs
        Threshold for the number of human messages before summarization is
        recommended. Defaults to :data:`MAX_HUMAN_MESSAGES`.

    Returns
    -------
    list[AnyMessage]:
        An abridged conversation history.
    """
    msgs = state["messages"]
    if not msgs:
        return []

    if hum_idxs := [
        i for i, msg in enumerate(msgs) if isinstance(msg, HumanMessage)
    ]:
        if max_hum_msgs is None:
            max_hum_msgs = MAX_HUMAN_MESSAGES

        start_idx = (
            hum_idxs[-max_hum_msgs]
            if len(hum_idxs) >= max_hum_msgs
            else hum_idxs[0]
        )
        out = msgs[start_idx:]
    else:
        out = msgs[:]

    summary = state["payload"].get("summary")
    if summary and include_summary:
        summ_msg = AIMessage(
            content=str(summary), name="summary", metadata={"summary": True}
        )
        return [summ_msg, *out]

    return out


def should_summarize(
    state: ConversationState,
    max_hum_msgs: int | None = None,
) -> bool:
    """Decide whether the conversation should be summarized.

    Parameters
    ----------
    state
        The current conversation state.
    max_hum_msgs
        Threshold for the number of human messages before summarization is
        recommended. Defaults to :data:`MAX_HUMAN_MESSAGES`.

    Returns
    -------
    bool
        ``True`` if the number of human messages exceeds the threshold,
        ``False`` otherwise.
    """
    msgs = state["messages"]
    if not msgs:
        return False
    if max_hum_msgs is None:
        max_hum_msgs = MAX_HUMAN_MESSAGES
    return sum(isinstance(m, HumanMessage) for m in msgs) > max_hum_msgs
