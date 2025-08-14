# --- orca_chat/graph/nodes/tools.py ------------------------------------------

"""..."""

from collections.abc import Sequence
from typing import Final

from langchain_core.tools import BaseTool
from langgraph.prebuilt import ToolNode

__all__: Final = [
    "tools_node",
]


def tools_node(tools: Sequence[BaseTool]) -> ToolNode:
    """Execute tool calls in the last AI message."""
    return ToolNode(tools=tools)
