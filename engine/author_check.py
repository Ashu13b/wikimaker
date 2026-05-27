"""Author name verification for sources.

When a paper is added, fetch its author list from CrossRef and check whether
the person we're researching actually appears as an author.

The challenge: "P.S. Yadav" matches both "Prem Singh Yadav" and
"Prem Shankar Singh Yadav". We use affiliation to disambiguate.
"""
from __future__ import annotations
import re
import requests

CROSSREF_API = "https://api.crossref.org/works"
TIMEOUT = 8


def name_variants(full_name: str) -> list[str]:
    """Return all lowercase abbreviation forms of a full name.

    "Prem Singh Yadav" → [
        "prem singh yadav",
        "p.s. yadav",  "p. s. yadav",  "ps yadav",
        "prem s. yadav",  "p. singh yadav",  "p.singh yadav",
    ]
    """
    parts = full_name.strip().split()
    if len(parts) < 2:
        return [full_name.lower()]

    first = parts[0].lower()
    last = parts[-1].lower()
    middles = [p.lower() for p in parts[1:-1]]

    variants: list[str] = [full_name.lower()]

    # Abbreviate all non-last parts (all lowercase)
    abbrev_parts = [p[0] for p in [first] + middles]

    # ps yadav
    variants.append("".join(abbrev_parts) + " " + last)
    # p.s. yadav
    variants.append(".".join(abbrev_parts) + ". " + last)
    # p. s. yadav
    variants.append(" ".join(p + "." for p in abbrev_parts) + " " + last)

    # Keep first name, abbreviate middles only — prem s. yadav
    if middles:
        abbrev_mid = " ".join(m[0] + "." for m in middles)
        variants.append(f"{first} {abbrev_mid} {last}")
        variants.append(f"{first} {''.join(m[0] for m in middles)} {last}")

    # Abbreviate first, keep middles — p. singh yadav
    for m in middles:
        variants.append(f"{first[0]}. {m} {last}")
        variants.append(f"{first[0]}.{m} {last}")

    return list(dict.fromkeys(v.strip() for v in variants))  # dedupe preserving order


def _normalise(name: str) -> str:
    """Lowercase, collapse spaces, strip dots for fuzzy comparison."""
    return re.sub(r"[.\s]+", " ", name.lower()).strip()


def _author_matches_variants(author_given: str, author_family: str, variants: list[str]) -> bool:
    full = f"{author_given} {author_family}".strip()
    normed = _normalise(full)
    normed_variants = [_normalise(v) for v in variants]

    if normed in normed_variants:
        return True

    # Also try family-name-only abbreviated forms
    for v in normed_variants:
        v_parts = v.split()
        if not v_parts:
            continue
        last_v = v_parts[-1]
        if _normalise(author_family) == last_v:
            # Last name matches — check initials
            initials_from_variant = "".join(p[0] for p in v_parts[:-1])
            initials_from_author = "".join(p[0] for p in author_given.split())
            if initials_from_variant and initials_from_author.startswith(initials_from_variant):
                return True

    return False


def _affiliation_matches(author_affils: list[dict], known_affiliation: str) -> bool | None:
    """True = strong match, False = clearly different, None = unknown."""
    if not author_affils:
        return None
    affil_text = " ".join(a.get("name", "") for a in author_affils).lower()
    if not affil_text.strip():
        return None

    # Build keyword list from known affiliation
    keywords = [w.lower() for w in known_affiliation.split() if len(w) > 3]
    matched = sum(1 for kw in keywords if kw in affil_text)
    if matched >= 1:
        return True
    # Check known domain keywords too
    if any(kw in affil_text for kw in ["icar", "cirb", "buffalo", "hisar"]):
        return True
    return False


def check_doi_authors(
    doi: str,
    person_name: str,
    person_affiliation: str = "",
) -> dict:
    """
    Returns:
        {
          "status": "confirmed" | "possible" | "wrong_person" | "not_found" | "no_data",
          "matched_author": str,     # as it appears in the paper
          "matched_affiliation": str,
          "all_authors": list[str],  # all author names on the paper
          "paper_title": str,
        }
    """
    try:
        resp = requests.get(f"{CROSSREF_API}/{doi}", timeout=TIMEOUT)
        if not resp.ok:
            return {"status": "no_data", "matched_author": "", "matched_affiliation": "", "all_authors": [], "paper_title": ""}
        msg = resp.json().get("message", {})
    except Exception:
        return {"status": "no_data", "matched_author": "", "matched_affiliation": "", "all_authors": [], "paper_title": ""}

    paper_title = " ".join(msg.get("title", []))
    authors = msg.get("author", [])
    all_names = [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in authors]

    variants = name_variants(person_name)

    for author in authors:
        given = author.get("given", "")
        family = author.get("family", "")
        if not family:
            continue

        if not _author_matches_variants(given, family, variants):
            continue

        affils = author.get("affiliation", [])
        matched_affil = " ".join(a.get("name", "") for a in affils).strip()
        full_author = f"{given} {family}".strip()

        # Full name exact match (3+ tokens) is unambiguous — no affiliation needed
        full_name_match = _normalise(full_author) == _normalise(person_name)
        if full_name_match:
            return {"status": "confirmed", "matched_author": full_author, "matched_affiliation": matched_affil, "all_authors": all_names, "paper_title": paper_title}

        # Abbreviated match — need affiliation to disambiguate
        if person_affiliation:
            affil_ok = _affiliation_matches(affils, person_affiliation)
            if affil_ok is True:
                return {"status": "confirmed", "matched_author": full_author, "matched_affiliation": matched_affil, "all_authors": all_names, "paper_title": paper_title}
            elif affil_ok is False:
                return {"status": "wrong_person", "matched_author": full_author, "matched_affiliation": matched_affil, "all_authors": all_names, "paper_title": paper_title}

        # Abbreviated match, affiliation unknown or not provided
        return {"status": "possible", "matched_author": full_author, "matched_affiliation": matched_affil, "all_authors": all_names, "paper_title": paper_title}

    return {"status": "not_found", "matched_author": "", "matched_affiliation": "", "all_authors": all_names, "paper_title": paper_title}


def extract_doi(url: str) -> str | None:
    """Extract DOI from a doi.org URL or inline DOI pattern."""
    m = re.search(r'(10\.\d{4,}/[^\s"<>?#]+)', url)
    return m.group(1) if m else None
