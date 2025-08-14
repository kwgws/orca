# --- orca_chat/graph/state.py ------------------------------------------------

"""..."""

from typing import Final

from langchain_core.messages import AIMessage, BaseMessage
from langgraph.graph.message import Messages, MessagesState, add_messages

__all__: Final = [
    "State",
    "add_msgs",
    "get_last_msg",
]


State = MessagesState


def add_msgs(state: State, msgs: Messages) -> State:
    """..."""

    return {"messages": add_messages(state["messages"], msgs)}  # type: ignore


def get_last_msg(
    state: State, *, msg_type: type[BaseMessage] = AIMessage
) -> BaseMessage | None:
    """Return most recent message of ``msg_type``."""

    try:
        return next(
            msg
            for msg in reversed(state["messages"])
            if isinstance(msg, msg_type)
        )
    except StopIteration:
        return None
