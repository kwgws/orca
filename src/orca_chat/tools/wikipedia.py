# orca_chat/tools/wikipedia.py

from typing import Final

from langchain_community.retrievers import WikipediaRetriever
from langchain_core.documents import Document
from langchain_core.tools import tool
from wikipedia import wikipedia

_DEFAULT_TOP_K: Final[int] = 8
_DEFAULT_MAX_CHARS: Final[int] = 4_000

__all__ = ["wikipedia_search"]


def _build_retriever(
    *,
    top_k_results=_DEFAULT_TOP_K,
    doc_content_chars_max=_DEFAULT_MAX_CHARS,
    lang="en",
) -> WikipediaRetriever:
    return WikipediaRetriever(
        wiki_client=wikipedia,
        top_k_results=top_k_results,
        doc_content_chars_max=doc_content_chars_max,
        lang=lang,
    )


def _pack(docs: list[Document], *, limit: int) -> list[dict[str, str | int]]:
    hits: list[dict[str, str | int]] = []

    for doc in docs[:limit]:
        meta = doc.metadata or {}
        hit: dict[str, str | int] = {
            "title": meta.get("title", meta.get("page_title", "")),
            "url": meta.get("source", meta.get("wikipedia_url", "")),
            "content": meta.get("summary", doc.page_content) or "",
            "chars": len(meta.get("summary", doc.page_content) or ""),
            "page_id": meta.get("page_id", meta.get("id", "")),
        }
        hits.append(hit)

    return hits


@tool
def wikipedia_search(query: str, k: int = 5) -> list[dict[str, str | int]]:
    """Search Wikipedia and return concise article candidates.

    Parameters
    ----------
    query
        The search string. Choose relevant keywords carefully. This is a very
        aggressive search algorithm. Think carefully and limit your search to
        the terms most likely to be associated with positive matches.
    k
        Maximum number of results to return after packing.

    Returns
    -------
    dict
        A list of results, each stored in a dictionary like so:
        ``{"title", "url", "summary", "chars", "page_id"}``.
    """
    # Fetch extra so (TODO) re-ranker has room to work.
    fetch_k = max(k, _DEFAULT_TOP_K)
    retriever = _build_retriever(top_k_results=fetch_k)
    docs = retriever.get_relevant_documents(query)
    return _pack(docs, limit=k)
