# orca_chat/cli.py

"""Demo CLI

A tiny asynchronous REPL that:
- reads a line from StdIn,
- appends it as a `HumanMessage` to the per-session state,
- invokes the compiled LangGraph workflow,
- streams the LLM reply via the built-in `StreamStdOut` callback.

All conversation state lives in the `state` dict that we keep in memory
between turns.
"""

import asyncio
import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import cast

from langchain_core.callbacks import StreamingStdOutCallbackHandler
from langchain_core.messages import HumanMessage
from langchain_core.messages.base import messages_to_dict

from .graph import ConversationState, build_graph
from .tools.wikipedia import wikipedia_search

__all__ = ["run"]


def run() -> None:
    try:
        asyncio.run(_chat())
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception:
        raise


async def _user_input() -> AsyncIterator[str]:
    loop = asyncio.get_running_loop()
    while True:
        try:
            line = await loop.run_in_executor(
                None, lambda: input("\n> ").strip()
            )
        except EOFError:
            break
        if line.lower() in {"/exit", "/quit", "/bye"}:
            break
        yield line


async def _chat() -> None:
    graph = build_graph(tools=[wikipedia_search])
    state: ConversationState = {"messages": [], "payload": {}}

    log_file = Path("logs/cli_session.json")
    log_file.parent.mkdir(parents=True, exist_ok=True)

    async for line in _user_input():
        state["messages"].append(HumanMessage(line))
        try:
            state = cast(
                ConversationState,
                await graph.ainvoke(
                    state,
                    config={"callbacks": [StreamingStdOutCallbackHandler()]},
                ),
            )
            _to_json(state, log_file)
        except asyncio.CancelledError:
            print("\nRequest cancelled.")
        except Exception:
            raise


def _to_json(state, path):
    payload = {
        "messages": messages_to_dict(state.get("messages", [])),
    }
    path.write_text(json.dumps(payload, indent=2))
