# --- orca_chat/interfaces/cli.py ---------------------------------------------

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
from langchain_core.runnables import RunnableConfig

from orca_chat.core import get_llm
from orca_chat.graph import State, add_msgs, make_graph

__all__ = [
    "run_cli",
]


def run_cli() -> None:
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
        if not line:
            continue
        if line.lower() in {"/exit", "/quit", "/bye"}:
            break
        yield line


async def _chat() -> None:
    llm = await get_llm()
    graph = make_graph(llm=llm, tools=[]).compile()

    state: State = {"messages": []}
    config: RunnableConfig = {"callbacks": [StreamingStdOutCallbackHandler()]}

    log_file = Path("logs/cli_session.json")
    log_file.parent.mkdir(parents=True, exist_ok=True)

    async for line in _user_input():
        state = add_msgs(state, [HumanMessage(line)])
        try:
            reply = await graph.ainvoke(state, config=config)
            state = cast(State, reply)
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
