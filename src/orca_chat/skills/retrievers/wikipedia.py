# import bs4
import wikipedia
from langchain_community.retrievers import WikipediaRetriever

__all__ = ["wiki_factory"]

# def _patched_bs4(*args, **kwargs):
#    kwargs.setdefault("features", "lxml")
#    return bs4.BeautifulSoup(*args, **kwargs)


# wikipedia.wikipedia.BeautifulSoup = _patched_bs4()


def wiki_factory(
    *,
    language="en",
    max_chars=4_000,
    top_k=10,
) -> WikipediaRetriever:
    return WikipediaRetriever(
        wiki_client=wikipedia,
        lang=language,
        doc_content_chars_max=max_chars,
        top_k_results=top_k,
    )
