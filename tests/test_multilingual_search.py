"""Unit tests for multilingual and bilingual search query expansion."""
from engine.multilingual_search import (
    detect_languages,
    transliterate_name,
    get_regional_news_outlets,
    build_bilingual_queries,
)


def test_detect_languages():
    assert "hi" in detect_languages("Indian")
    assert "fr" in detect_languages("French")
    assert "de" in detect_languages("German")
    assert "es" in detect_languages("Spanish")
    assert "ru" in detect_languages("Russian")
    # Indic name fallback
    assert "hi" in detect_languages(None, "Prem Singh Yadav")


def test_transliterate_name():
    assert transliterate_name("Prem Singh Yadav", "hi") == "प्रेम सिंह यादव"
    assert transliterate_name("Rajesh Kumar Sharma", "hi") == "राजेश कुमार शर्मा"


def test_get_regional_news_outlets():
    outlets_hi = get_regional_news_outlets("Indian")
    assert "amarujala.com" in outlets_hi
    assert "bhaskar.com" in outlets_hi

    outlets_fr = get_regional_news_outlets("French")
    assert "lemonde.fr" in outlets_fr


def test_build_bilingual_queries_hindi():
    queries = build_bilingual_queries(
        name="Prem Singh Yadav",
        nationality="Indian",
        affiliation="ICAR-CIRB",
        field="Animal Biotechnology",
        slot="known_for",
    )
    # Check that both English and Devanagari queries are generated
    assert any('"Prem Singh Yadav"' in q for q in queries)
    assert any("प्रेम सिंह यादव" in q for q in queries)
    assert any("शोध" in q or "अनुसंधान" in q or "योगदान" in q for q in queries)


def test_build_bilingual_queries_french():
    queries = build_bilingual_queries(
        name="Alain Aspect",
        nationality="French",
        affiliation="Institut d'Optique",
        slot="award",
    )
    assert any('"Alain Aspect"' in q for q in queries)
    assert any("prix" in q or "distinction" in q for q in queries)


def test_build_bilingual_queries_german():
    queries = build_bilingual_queries(
        name="Stefan Hell",
        nationality="German",
        affiliation="Max Planck Institute",
        slot="birth_date",
    )
    assert any('"Stefan Hell"' in q for q in queries)
    assert any("Geburtsdatum" in q or "geboren" in q for q in queries)
