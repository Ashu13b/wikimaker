"""Central publisher and domain classification registry for Wikimaker.

Consolidates independent news outlets, academic publishers, institutional/primary
sites, self-published platforms, and unreliable mirrors into a single source of truth.
"""
from __future__ import annotations
from urllib.parse import urlparse


def extract_domain(url: str | None) -> str:
    """Extract clean lowercase domain from URL, stripping www. and sub-paths."""
    if not url:
        return ""
    try:
        host = (urlparse(url).hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return ""


INDEPENDENT_NEWS_DOMAINS: set[str] = {
    # International Major Outlets
    "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk", "nytimes.com",
    "theguardian.com", "washingtonpost.com", "wsj.com", "bloomberg.com",
    "ft.com", "theatlantic.com", "economist.com",
    # Indian National & Business Press
    "thehindu.com", "thehindubusinessline.com", "indianexpress.com",
    "timesofindia.indiatimes.com", "timesofindia.com", "indiatimes.com", "hindustantimes.com",
    "business-standard.com", "moneycontrol.com", "livemint.com",
    "ndtv.com", "theprint.in", "scroll.in", "thewire.in", "thequint.com",
    "firstpost.com", "theweek.in", "financialexpress.com", "outlookindia.com",
    "newindianexpress.com", "thestatesman.com", "deccanherald.com",
    "indiatoday.in", "telegraphindia.com", "tribuneindia.com",
    # Indian Regional & Language Press (Editorial / Investigative)
    "amarujala.com", "jagran.com", "dainikjagran.com", "bhaskar.com",
    "dainikbhaskar.com", "divyabhaskar.co.in", "punjabkesari.in",
    "punjabkesari.com", "news18.com", "tv9hindi.com", "tv9.com",
    "abplive.com", "aajtak.in", "zeenews.india.com", "india.com",
    "patrika.com", "navbharattimes.indiatimes.com", "etvbharat.com",
    "kisantak.in", "devdiscourse.com", "livevns.news",
    "webdunia.com", "krishijagran.com", "krishakjagat.org",
    # Entertainment & Trade Press (Independent Editorial)
    "variety.com", "hollywoodreporter.com", "billboard.com",
    "rollingstone.com", "pitchfork.com", "allmusic.com", "filmfare.com",
    "bollywoodhungama.com", "pinkvilla.com", "koimoi.com", "mid-day.com",
    "freepressjournal.in",
}

ACADEMIC_PUBLISHER_DOMAINS: set[str] = {
    "nature.com", "science.org", "sciencedirect.com", "springer.com",
    "wiley.com", "tandfonline.com", "oup.com", "cambridge.org",
    "biomedcentral.com", "plos.org", "ieee.org", "acm.org", "cell.com",
    "bmj.com", "thelancet.com", "nejm.org", "asm.org", "frontiersin.org",
    "mdpi.com", "hindawi.com", "semanticscholar.org", "jstor.org",
}

PRIMARY_OR_INSTITUTIONAL_DOMAINS: set[str] = {
    "icar.org.in", "icar.gov.in", "cirb.res.in", "dst.gov.in", "dbt.gov.in",
    "csir.res.in", "pib.gov.in", "orcid.org", "doi.org",
    "ncbi.nlm.nih.gov", "pubmed.ncbi.nlm.nih.gov", "satishserial.com",
    "acspublisher.com", "intechopen.com", "ndri.res.in", "bhu.ac.in",
}

RECORD_REGISTRY_DOMAINS: set[str] = {
    "indiabookofrecords.in", "limcabookofrecords.in", "guinnessworldrecords.com",
}

SELF_PUBLISHED_DOMAINS: set[str] = {
    "researchgate.net", "academia.edu", "linkedin.com", "twitter.com",
    "x.com", "facebook.com", "instagram.com", "youtube.com",
    "music.youtube.com", "youtu.be", "open.spotify.com", "music.apple.com",
    "soundcloud.com", "tiktok.com", "medium.com", "wordpress.com",
    "blogspot.com", "github.io", "reddit.com", "quora.com",
}

UNRELIABLE_DOMAINS: set[str] = {
    "imdb.com", "m.imdb.com", "fandom.com", "wikia.com", "grokipedia.com",
    "celebsagewiki.com", "famousbirthdays.com", "bookmyshow.com",
    "district.in", "ticketmaster.com", "insider.in", "dbpedia.org",
    "wikidata.org",
    # citation aggregators and content farms (namesake contamination risk)
    "scispace.com", "scilit.net", "gpatindia.com",
}


def matches_domain_set(domain: str, domain_set: set[str]) -> bool:
    """Check if domain equals or is a subdomain of any entry in domain_set."""
    if not domain:
        return False
    return any(domain == d or domain.endswith("." + d) for d in domain_set)


def is_independent_secondary_news(url: str) -> bool:
    """Check if a URL belongs to a recognized independent secondary news publisher."""
    domain = extract_domain(url)
    if matches_domain_set(domain, PRIMARY_OR_INSTITUTIONAL_DOMAINS):
        return False
    return matches_domain_set(domain, INDEPENDENT_NEWS_DOMAINS)


def is_primary_or_institutional(url: str) -> bool:
    """Check if a URL belongs to an institutional or primary source domain."""
    domain = extract_domain(url)
    return matches_domain_set(domain, PRIMARY_OR_INSTITUTIONAL_DOMAINS)
