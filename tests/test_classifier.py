"""Unit tests for the source reliability classifier."""
from engine.classifier import classify_sources
from engine.models import Source, SourceReliability


class _ExplodingProvider:
    """Fails loudly if the LLM path is reached — the domain fast path must handle it."""

    def complete(self, system: str, user: str) -> str:
        raise AssertionError("LLM path should not run for known news domains")


class _JsonProvider:
    def __init__(self, response: str):
        self.response = response

    def complete(self, system: str, user: str) -> str:
        return self.response


def test_known_news_domains_classify_without_llm():
    sources = [
        Source(url="https://hindi.news18.com/news/haryana/hisar-clone", title="t", publisher="news18"),
        Source(url="https://www.etvbharat.com/hi/!state/some-article", title="t", publisher="etv"),
        Source(url="https://www.bhaskar.com/local/haryana/hisar/news/x", title="t", publisher="bhaskar"),
        Source(url="https://sgttimes.com/faculty-of-agriculture-sciences", title="t", publisher="sgt"),
    ]
    classify_sources(sources, _ExplodingProvider())
    assert all(s.reliability == SourceReliability.reliable_secondary for s in sources)


def test_known_primary_domains_classify_without_llm():
    source = Source(url="https://cirb.res.in/hisar-1/", title="t", publisher="cirb")
    classify_sources([source], _ExplodingProvider())
    assert source.reliability == SourceReliability.primary


def test_unknown_domain_uses_llm_reliability_field():
    source = Source(url="https://example-news-portal.example/breaking", title="t", publisher="portal")
    provider = _JsonProvider('{"reliability": "reliable_secondary", "reason": "independent press"}')
    classify_sources([source], provider)
    assert source.reliability == SourceReliability.reliable_secondary
