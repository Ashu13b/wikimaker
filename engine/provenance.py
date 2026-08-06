"""Strict Provenance & Trust Scoring engine for sources and claims."""
from __future__ import annotations
from urllib.parse import urlparse
from .models import Source, Claim, SourceReliability, PersonProfile, VerificationState

def normalize_url(url: str | None) -> str:
    if not url:
        return ""
    u = url.strip().lower()
    if u.startswith("https://"):
        u = u[8:]
    elif u.startswith("http://"):
        u = u[7:]
    if u.startswith("www."):
        u = u[4:]
    if "#" in u:
        u = u.split("#", 1)[0]
    if "?" in u:
        u = u.split("?", 1)[0]
    if u.endswith("/"):
        u = u[:-1]
    return u

HIGH_TRUST_DOMAINS = {
    "nature.com", "science.org", "sciencedirect.com", "bbc.com", "bbc.co.uk",
    "nytimes.com", "theguardian.com", "washingtonpost.com", "reuters.com",
    "apnews.com", "thehindu.com", "indianexpress.com", "timesofindia.indiatimes.com",
    "biomedcentral.com", "plos.org", "ieee.org", "acm.org", "springer.com",
    "wiley.com", "tandfonline.com", "oup.com", "cambridge.org", "ncbi.nlm.nih.gov"
}

MEDIUM_TRUST_DOMAINS = {
    "wikipedia.org", "wikidata.org", "britannica.com", "researchgate.net",
    "academia.edu", "semanticscholar.org", "orcid.org"
}

UNTRUSTED_DOMAINS = {
    "medium.com", "wordpress.com", "blogspot.com", "github.io", "linkedin.com",
    "facebook.com", "twitter.com", "x.com", "reddit.com", "quora.com"
}

RECORD_REGISTRY_DOMAINS = {
    "indiabookofrecords.in", "limcabookofrecords.in",
}


def get_domain_trust(url: str) -> str:
    """Return 'high', 'medium', 'low', or 'untrusted' domain trust level based on hostname."""
    if not url:
        return "low"
    try:
        domain = urlparse(url).netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        
        def match_domain(target_set: set[str]) -> bool:
            return any(domain == d or domain.endswith("." + d) for d in target_set)

        # Check explicit domain sets with subdomain support
        if match_domain(HIGH_TRUST_DOMAINS):
            return "high"
        if match_domain(UNTRUSTED_DOMAINS):
            return "untrusted"
        if match_domain(MEDIUM_TRUST_DOMAINS):
            return "medium"

        # Check domain extensions / TLDs
        if domain.endswith((".gov", ".gov.in", ".gov.uk", ".edu", ".ac.uk", ".ac.in", ".res.in", ".edu.au")):
            return "high"
        if domain.endswith((".org", ".edu")):
            return "medium"
        return "low"
    except Exception:
        return "low"


def classify_source_provenance(source: Source, subject_name: str = "") -> Source:
    """Determine source independence, domain trust, and provenance category."""
    domain_trust = get_domain_trust(source.url)
    source.domain_trust = domain_trust

    url_lower = (source.url or "").lower()
    pub_lower = (source.publisher or "").lower()

    # Record registries verify that a registry made a recognition, but they are
    # the issuing body rather than independent coverage of the subject.
    try:
        hostname = urlparse(source.url).netloc.lower()
        if hostname.startswith("www."):
            hostname = hostname[4:]
    except Exception:
        hostname = ""
    if any(hostname == domain or hostname.endswith("." + domain) for domain in RECORD_REGISTRY_DOMAINS):
        source.provenance_category = "record_registry"
        source.is_independent = False
        source.reliability = SourceReliability.primary
        return source

    # Academic authored publication
    if (
        source.fetched_by == "semantic_scholar"
        or source.author_match_status in ("confirmed", "possible")
        or any(k in url_lower for k in ("doi.org", "arxiv.org", "paper", "article/abstract"))
        or "journal" in pub_lower
    ):
        source.provenance_category = "authored_publication"
        source.is_independent = False
        source.reliability = SourceReliability.primary
        return source

    # Institutional bio / faculty profile
    is_inst_domain = any(k in url_lower for k in (".edu", ".ac.", ".res.in")) or any(k in pub_lower for k in ("university", "institute", "college", "school of"))
    is_icar_domain = any(k in url_lower for k in ("cirb.res.in", "icar.org.in", "icar.gov.in"))
    is_inst_path = any(k in url_lower for k in ("/faculty/", "/staff/", "/people/", "/directory/", "/person/", "/cv/", "faculty-profile"))
    
    if is_icar_domain or (is_inst_domain and (is_inst_path or "bio" in url_lower or "profile" in url_lower)) or (is_inst_path and "news" not in pub_lower):
        source.provenance_category = "institutional_bio"
        source.is_independent = False
        source.reliability = SourceReliability.primary
        return source

    # Self-published / social / blog
    if domain_trust == "untrusted" or any(k in url_lower for k in ("blog", "personal", "github.io", "linkedin")):
        source.provenance_category = "self_published"
        source.is_independent = False
        source.reliability = SourceReliability.self_published
        return source

    # Independent secondary coverage (news, reputable magazine, encyclopedia)
    if domain_trust in ("high", "medium") or source.fetched_by in ("google_search", "duckduckgo", "crawl"):
        source.provenance_category = "independent_secondary"
        source.is_independent = True
        source.reliability = SourceReliability.reliable_secondary
        return source

    source.provenance_category = "general_web"
    source.is_independent = True
    return source


def evaluate_claim_trust(claim: Claim, source: Source | None, profile: PersonProfile | None = None) -> Claim:
    """Calculate trust score (0.0-1.0) and provenance status for a claim."""
    if not source or not claim.source_url:
        claim.trust_score = 0.2 if claim.user_provided else 0.0
        claim.provenance_status = "unverified"
        claim.is_independent = False
        return claim

    base_score = 0.5
    # Domain trust weight
    domain_trust = getattr(source, "domain_trust", get_domain_trust(source.url))
    if domain_trust == "high":
        base_score += 0.25
    elif domain_trust == "medium":
        base_score += 0.15
    elif domain_trust == "untrusted":
        base_score -= 0.3

    # Source independence & reliability weight
    is_indep = getattr(source, "is_independent", True)
    category = getattr(source, "provenance_category", "general_web")
    claim.is_independent = is_indep

    if is_indep and category == "independent_secondary":
        base_score += 0.15
    elif category in ("institutional_bio", "authored_publication", "record_registry"):
        base_score += 0.05
    elif category == "self_published":
        base_score -= 0.2

    # Verification state weight
    if claim.verification == VerificationState.confirmed:
        base_score += 0.1
    elif claim.verification == VerificationState.edited:
        base_score += 0.05

    # Verbatim date context presence weight
    if claim.date_context:
        base_score += 0.05

    trust_score = round(max(0.0, min(1.0, base_score)), 2)
    claim.trust_score = trust_score

    if trust_score >= 0.7 and is_indep:
        claim.provenance_status = "verified_independent"
    elif category in ("institutional_bio", "authored_publication", "record_registry") or not is_indep:
        claim.provenance_status = "primary_sourced"
    else:
        claim.provenance_status = "unverified"

    return claim
