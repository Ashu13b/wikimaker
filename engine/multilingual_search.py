"""Multilingual & bilingual search expansion engine.

Ensures that source discovery is not limited to English-only queries,
expanding searches into the subject's native country language and script
(e.g., Hindi/Devanagari for Indian subjects, French, German, Spanish, Russian, etc.)
so that local and regional secondary coverage is not missed.
"""
from __future__ import annotations

# ── Language Detection by Nationality / Name ──────────────────────────────────

_NATIONALITY_TO_LANGUAGES: dict[str, list[str]] = {
    "indian": ["hi"],
    "india": ["hi"],
    "french": ["fr"],
    "france": ["fr"],
    "german": ["de"],
    "germany": ["de"],
    "austrian": ["de"],
    "swiss": ["de", "fr"],
    "spanish": ["es"],
    "spain": ["es"],
    "mexican": ["es"],
    "mexico": ["es"],
    "argentinian": ["es"],
    "argentine": ["es"],
    "colombian": ["es"],
    "chilean": ["es"],
    "russian": ["ru"],
    "russia": ["ru"],
    "italian": ["it"],
    "italy": ["it"],
    "japanese": ["ja"],
    "japan": ["ja"],
    "chinese": ["zh"],
    "china": ["zh"],
    "brazilian": ["pt"],
    "brazil": ["pt"],
    "portuguese": ["pt"],
    "portugal": ["pt"],
}

# Common transliteration mappings for Indic names to Devanagari script
_INDIC_PHONETIC_MAP: dict[str, str] = {
    "prem": "प्रेम",
    "singh": "सिंह",
    "yadav": "यादव",
    "kumar": "कुमार",
    "sharma": "शर्मा",
    "verma": "वर्मा",
    "gupta": "गुप्ता",
    "lal": "लाल",
    "rao": "राव",
    "reddy": "रेड्डी",
    "patel": "पटेल",
    "mishra": "मिश्रा",
    "joshi": "जोशी",
    "nair": "नायर",
    "das": "दास",
    "sen": "सेन",
    "banerjee": "मुखर्जी",
    "chatterjee": "चटर्जी",
    "mukherjee": "मुखर्जी",
    "bhattacharya": "भट्टाचार्य",
    "agarwal": "अग्रवाल",
    "aggarwal": "अग्रवाल",
    "mehta": "मेहता",
    "shah": "शाह",
    "chaudhary": "चौधरी",
    "choudhary": "चौधरी",
    "pandey": "पांडेय",
    "tiwari": "तिवारी",
    "tripathi": "त्रिपाठी",
    "dubey": "दुबे",
    "shukla": "शुक्ला",
    "rajesh": "राजेश",
    "suresh": "सुरेश",
    "ramesh": "रमेश",
    "anil": "अनिल",
    "sunil": "सुनील",
    "vikram": "विक्रम",
    "vijay": "विजय",
    "sanjay": "संजय",
    "ajay": "अजय",
    "amit": "अमित",
    "arun": "अरुण",
    "ashok": "अशोक",
    "deepak": "दीपक",
    "manoj": "मनोज",
    "sandeep": "संदीप",
    "alok": "आलोक",
    "pradeep": "प्रदीप",
}

# ── Localized Terminology per Language and Slot ───────────────────────────────

_LOCALIZED_SLOT_TERMS: dict[str, dict[str, list[str]]] = {
    "hi": {
        "general": ["समाचार रिपोर्ट", "साक्षात्कार", "जीवनी"],
        "birth_date": ["जन्म तिथि जीवनी", "जन्म दिन"],
        "birth_place": ["जन्म स्थान पैतृक गाँव", "निवास स्थान"],
        "education": ["शिक्षा विश्वविद्यालय डिग्री पीएचडी", "स्नातक उपाधि"],
        "position": ["वैज्ञानिक पद नियुक्ति", "निदेशक प्रमुख"],
        "affiliation": ["संस्थान विश्वविद्यालय केंद्र", "प्रयोगशाला"],
        "award": ["पुरस्कार सम्मान पदक", "फेलोशिप प्रशस्ति"],
        "known_for": ["प्रमुख शोध योगदान", "उपलब्धि अनुसंधान कार्य", "आविष्कार तकनीक"],
        "field": ["कार्यक्षेत्र विशेषज्ञता", "अनुसंधान विषय"],
    },
    "fr": {
        "general": ["actualités", "reportage presse", "interview biographie"],
        "birth_date": ["date de naissance biographie", "né en"],
        "birth_place": ["lieu de naissance originaire de"],
        "education": ["formation diplôme doctorat université thèse"],
        "position": ["poste chercheur directeur professeur"],
        "affiliation": ["institut laboratoire université CNRS"],
        "award": ["prix distinction médaille récompense"],
        "known_for": ["recherche découverte travaux majeurs percée"],
        "field": ["domaine spécialité recherche"],
    },
    "de": {
        "general": ["Nachrichten Pressebericht", "Interview Porträt"],
        "birth_date": ["Geburtsdatum Biographie", "geboren am"],
        "birth_place": ["Geburtsort Herkunft"],
        "education": ["Ausbildung Studium Promotion Doktor Universität"],
        "position": ["Position Wissenschaftler Professor Leiter"],
        "affiliation": ["Institut Universität Max-Planck Forschungszentrum"],
        "award": ["Auszeichnung Preis Ehrung Medaille"],
        "known_for": ["Forschung Entdeckung Hauptbeitrag Durchbruch"],
        "field": ["Fachgebiet Forschungsschwerpunkt"],
    },
    "es": {
        "general": ["noticias prensa", "entrevista semblanza biografía"],
        "birth_date": ["fecha de nacimiento biografía", "nacido en"],
        "birth_place": ["lugar de nacimiento origen"],
        "education": ["educación universidad licenciatura doctorado tesis"],
        "position": ["cargo investigador director profesor"],
        "affiliation": ["instituto universidad CSIC centro de investigación"],
        "award": ["premio galardón distinción medalla"],
        "known_for": ["investigación descubrimiento contribución científica"],
        "field": ["especialidad campo de estudio"],
    },
    "ru": {
        "general": ["новости статья", "интервью биография"],
        "birth_date": ["дата рождения биография", "родился"],
        "birth_place": ["место рождения"],
        "education": ["образование университет диссертация степень"],
        "position": ["должность ученый заведующий директор"],
        "affiliation": ["институт академия наук РАН университет"],
        "award": ["награда премия звание медаль лауреат"],
        "known_for": ["научный вклад открытие разработка исследования"],
        "field": ["научное направление специальность"],
    },
}

_COUNTRY_NEWS_OUTLETS: dict[str, list[str]] = {
    "hi": [
        "amarujala.com", "bhaskar.com", "jagran.com", "punjabkesari.com",
        "patrika.com", "etvbharat.com", "kisantak.in", "navbharattimes.indiatimes.com",
    ],
    "fr": [
        "lemonde.fr", "lefigaro.fr", "liberation.fr", "france24.com", "leparisien.fr",
    ],
    "de": [
        "spiegel.de", "zeit.de", "faz.net", "sueddeutsche.de", "welt.de",
    ],
    "es": [
        "elpais.com", "elmundo.es", "abc.es", "lanacion.com.ar", "eluniversal.com.mx",
    ],
    "ru": [
        "tass.ru", "ria.ru", "rbc.ru", "kommersant.ru", "vedomosti.ru",
    ],
}


def detect_languages(nationality: str | None, name: str | None = None) -> list[str]:
    """Detect local languages associated with the person's nationality or name."""
    langs: list[str] = []
    if nationality:
        nat_lower = nationality.lower().strip()
        for key, detected in _NATIONALITY_TO_LANGUAGES.items():
            if key in nat_lower:
                for lang_code in detected:
                    if lang_code not in langs:
                        langs.append(lang_code)

    # Fallback to Indic name detection if no nationality given
    if not langs and name:
        tokens = [t.lower().strip(".,") for t in name.split()]
        if any(t in _INDIC_PHONETIC_MAP for t in tokens):
            langs.append("hi")

    return langs


def transliterate_name(name: str, target_lang: str) -> str | None:
    """Attempt transliteration of a romanized name into native script."""
    if target_lang == "hi":
        tokens = [t.lower().strip(".,") for t in name.split()]
        devanagari_tokens = [_INDIC_PHONETIC_MAP.get(t) for t in tokens if t in _INDIC_PHONETIC_MAP]
        if len(devanagari_tokens) >= 2 or len(devanagari_tokens) == len(tokens):
            return " ".join(t for t in devanagari_tokens if t)
    return None


def get_regional_news_outlets(nationality: str | None, name: str | None = None) -> list[str]:
    """Return list of top regional/vernacular press domains for the subject's region."""
    langs = detect_languages(nationality, name)
    outlets: list[str] = []
    for lang in langs:
        for domain in _COUNTRY_NEWS_OUTLETS.get(lang, []):
            if domain not in outlets:
                outlets.append(domain)
    return outlets


def build_bilingual_queries(
    name: str,
    nationality: str | None = None,
    affiliation: str | None = None,
    field: str | None = None,
    slot: str | None = None,
    hint: str | None = None,
    limit: int = 8,
) -> list[str]:
    """Generate balanced search queries spanning English and native country languages.

    Produces both international English disambiguated queries and localized
    vernacular queries so regional coverage is not overlooked.
    """
    queries: list[str] = []
    disambig = ""
    if affiliation:
        tokens = [t for t in affiliation.replace("-", " ").split() if len(t) > 3]
        if tokens:
            disambig = tokens[0]
    elif field:
        tokens = [t for t in field.replace("-", " ").split() if len(t) > 3]
        if tokens:
            disambig = tokens[0]

    # 1. Primary English query
    base_en = f'"{name}"'
    if disambig:
        base_en += f" {disambig}"
    if hint:
        base_en += f" {hint}"
    queries.append(base_en.strip())

    # 2. Localized / vernacular queries. Carry the hint (often a year, venue,
    # or event name) into native-script queries too; otherwise a date-centric
    # targeted search silently falls back to name-only Hindi terms.
    target_langs = detect_languages(nationality, name)
    for lang in target_langs:
        trans_name = transliterate_name(name, lang)
        slot_dict = _LOCALIZED_SLOT_TERMS.get(lang, {})
        terms_to_use = slot_dict.get(slot or "general", slot_dict.get("general", []))

        for term in terms_to_use[:2]:
            # Query using native script name if available
            if trans_name:
                q_native = f'"{trans_name}" {term}'
                if disambig:
                    q_native += f" {disambig}"
                if hint:
                    q_native += f" {hint}"
                if q_native not in queries:
                    queries.append(q_native)

            # Query using English name + native language search terms
            q_bilingual = f'"{name}" {term}'
            if disambig:
                q_bilingual += f" {disambig}"
            if hint:
                q_bilingual += f" {hint}"
            if q_bilingual not in queries:
                queries.append(q_bilingual)

    # 3. English slot-specific query if slot is specified
    if slot:
        en_slot_terms = {
            "birth_date": "biography born date of birth",
            "birth_place": "biography birthplace born",
            "education": "education university degree PhD",
            "position": "scientist career appointment position",
            "award": "award prize honour medal",
            "known_for": "research contribution achievement",
        }
        if slot in en_slot_terms:
            q_slot = f'"{name}" {en_slot_terms[slot]}'
            if disambig:
                q_slot += f" {disambig}"
            if q_slot not in queries:
                queries.append(q_slot)

    return queries[:limit]
