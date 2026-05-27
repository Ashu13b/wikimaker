"""Source graph crawler — one source leads to more sources.

Each fetched page is a node. From it we extract:
  - Hyperlinks (follow if relevant to the person)
  - Named entity mentions (search for them)
  - DOI / paper citations (fetch from Semantic Scholar)

We build outward to depth=3, capping at max_nodes total.
"""
from __future__ import annotations
import re
import time
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup

from .models import Source, SourceReliability
from .fetcher import fetch_url, HEADERS

TIMEOUT = 10
S2_API = "https://api.semanticscholar.org/graph/v1"


@dataclass
class SourceNode:
    url: str
    text: str
    title: str
    publisher: str
    depth: int
    outlinks: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)   # named orgs/people found
    dois: list[str] = field(default_factory=list)        # DOIs found in text


@dataclass
class SourceGraph:
    nodes: dict[str, SourceNode] = field(default_factory=dict)   # url → node
    relevance_hits: dict[str, int] = field(default_factory=dict) # url → mention count

    def to_sources(self, classifier_fn) -> list[Source]:
        sources = []
        for url, node in self.nodes.items():
            sources.append(Source(
                url=url,
                title=node.title,
                publisher=node.publisher,
                reliability=SourceReliability.primary,  # classifier will re-tag
                snippet=node.text[:400],
            ))
        return sources


def crawl(
    seed_urls: list[str],
    person_name: str,
    keywords: list[str],
    max_nodes: int = 40,
    max_depth: int = 3,
) -> SourceGraph:
    """
    Start from seed_urls, follow relevant links outward to max_depth.
    Only follow links whose fetched content mentions person_name or keywords.
    """
    graph = SourceGraph()
    queue: list[tuple[str, int]] = [(u, 0) for u in seed_urls]
    visited: set[str] = set()
    name_tokens = set(person_name.lower().split())

    while queue and len(graph.nodes) < max_nodes:
        url, depth = queue.pop(0)
        if url in visited or depth > max_depth:
            continue
        visited.add(url)

        result = fetch_url(url)
        if result.blocked or not result.text:
            continue

        html = result.raw_html or result.text
        title, publisher = _extract_meta(html, url)
        links = _extract_links(html, url)
        entities = _extract_entities(result.text)
        dois = _extract_dois(result.text)

        node = SourceNode(
            url=url,
            text=result.text[:2000],
            title=title,
            publisher=publisher,
            depth=depth,
            outlinks=links,
            entities=entities,
            dois=dois,
        )
        graph.nodes[url] = node

        # Count how many times person is mentioned — relevance signal
        mentions = _count_mentions(result.text, person_name, keywords)
        graph.relevance_hits[url] = mentions

        if depth < max_depth:
            # Follow links whose anchor text or URL suggests relevance
            for link in links[:30]:
                if link not in visited and _is_relevant_link(link, html, person_name, keywords):
                    queue.append((link, depth + 1))

            # Follow DOIs via Semantic Scholar
            for doi in dois[:5]:
                doi_sources = _expand_doi(doi, person_name)
                for ds_url in doi_sources:
                    if ds_url not in visited:
                        queue.append((ds_url, depth + 1))

            # Search for named entities that might yield more sources
            for entity in entities[:3]:
                if _entity_worth_searching(entity, person_name):
                    search_urls = _search_entity(entity, person_name)
                    for su in search_urls[:2]:
                        if su not in visited:
                            queue.append((su, depth + 1))

        time.sleep(0.3)  # polite crawl delay

    return graph


def _extract_meta(html: str, url: str) -> tuple[str, str]:
    try:
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string.strip() if soup.title else url
        host = urlparse(url).netloc.replace("www.", "")
        return title, host
    except Exception:
        return url, urlparse(url).netloc


def _extract_links(html: str, base_url: str) -> list[str]:
    try:
        soup = BeautifulSoup(html, "html.parser")
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith(("javascript", "mailto", "#")):
                continue
            full = urljoin(base_url, href)
            parsed = urlparse(full)
            if parsed.scheme in ("http", "https"):
                links.append(full)
        return list(dict.fromkeys(links))  # deduplicate preserving order
    except Exception:
        return []


def _extract_dois(text: str) -> list[str]:
    return re.findall(r'10\.\d{4,}/[^\s"<>]+', text)


def _extract_entities(text: str) -> list[str]:
    """Extract capitalized multi-word phrases likely to be named entities."""
    # Simple heuristic: 2-4 consecutive capitalized words
    pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b'
    candidates = re.findall(pattern, text)
    # Filter to likely org/person names (not start of sentences)
    seen = set()
    result = []
    for c in candidates:
        if c not in seen and len(c) > 8:
            seen.add(c)
            result.append(c)
    return result[:20]


def _count_mentions(text: str, person_name: str, keywords: list[str]) -> int:
    text_lower = text.lower()
    count = text_lower.count(person_name.lower())
    # Abbreviated form (e.g., "PS Yadav" or "P.S. Yadav")
    parts = person_name.split()
    if len(parts) >= 2:
        abbrev = f"{parts[0][0]}. {parts[-1]}"
        count += text_lower.count(abbrev.lower())
    for kw in keywords:
        count += text_lower.count(kw.lower()) * 0.2  # keywords count less
    return int(count)


def _is_relevant_link(link: str, page_html: str, person_name: str, keywords: list[str]) -> bool:
    """Heuristic: is this link worth following?"""
    link_lower = link.lower()
    name_parts = [p.lower() for p in person_name.split()]

    # Skip navigation, static, and social links
    skip_patterns = [
        "login", "signup", "register", "cart", "shop", "privacy", "terms",
        "cookie", "sitemap", "rss", "feed", ".jpg", ".png", ".zip", ".gif",
        "facebook.com", "twitter.com", "instagram.com", "youtube.com",
        "screen-reader", "about-cirb", "iso-certificate", "organizational",
        "message-from", "vision-20", "cadre-strength", "sub-campus",
        "divisions-units", "animal-health-section", "other-units",
        "/page/", "?page=", "tag/", "category/", "author/",
        "contact", "careers", "tenders", "rti-", "circulars",
    ]
    if any(p in link_lower for p in skip_patterns):
        return False

    # Must be content-looking URL (has a slug with real words)
    path = urlparse(link).path
    if len(path) < 5 or path in ("/", "/news/", "/publications/"):
        return False

    # Prefer links whose URL contains person name or keywords
    if any(p in link_lower for p in name_parts):
        return True
    if any(kw.lower() in link_lower for kw in keywords):
        return True

    # Check anchor text on the page for person/keyword mentions
    try:
        soup = BeautifulSoup(page_html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if link.endswith(href) or href in link:
                anchor_text = a.get_text(strip=True).lower()
                if any(p in anchor_text for p in name_parts):
                    return True
                if any(kw.lower() in anchor_text for kw in keywords):
                    return True
    except Exception:
        pass

    return False


def _entity_worth_searching(entity: str, person_name: str) -> bool:
    """Skip entities that are just the person's name or too generic."""
    skip = {"India", "Indian", "New Delhi", "United States", "University", "Institute", "Research"}
    if entity in skip:
        return False
    if person_name.lower() in entity.lower():
        return False
    return True


def _search_entity(entity: str, person_name: str) -> list[str]:
    """DuckDuckGo search for entity + person name, return result URLs."""
    try:
        resp = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": f'"{entity}" "{person_name}"', "format": "json", "no_html": "1"},
            headers=HEADERS, timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        urls = []
        if data.get("AbstractURL"):
            urls.append(data["AbstractURL"])
        for topic in data.get("RelatedTopics", [])[:3]:
            if isinstance(topic, dict) and topic.get("FirstURL"):
                urls.append(topic["FirstURL"])
        return urls
    except Exception:
        return []


def _expand_doi(doi: str, person_name: str) -> list[str]:
    """From a DOI, get papers that cite it — those are independent RS about the work."""
    try:
        resp = requests.get(
            f"{S2_API}/paper/DOI:{doi}/citations",
            params={"fields": "externalIds,title", "limit": 5},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        urls = []
        for item in data:
            citing_doi = item.get("citingPaper", {}).get("externalIds", {}).get("DOI")
            if citing_doi:
                urls.append(f"https://doi.org/{citing_doi}")
        return urls
    except Exception:
        return []
