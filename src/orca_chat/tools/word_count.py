# orca_chat/skills/tools/wordcount.py

from typing import Any

from langchain_core.tools import tool


@tool
def word_count(text: str) -> dict[str, Any]:
    """Return {"word_count": N} where N is the number of words in `text`."""
    count = len(text.split())
    print(f"[word_count] counted {count} words")
    return {"word_count": count}
