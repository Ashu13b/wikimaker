# Wikipedia AfC Review & Draft Hardening Protocol

This document establishes the comprehensive pre-submission review framework, quality assurance heuristics, and evidence-hardening strategies implemented in Wikimaker to guarantee acceptance under Wikipedia's Articles for Creation (AfC) review process.

---

## 1. The 5 Core AfC Decline Vectors & Built-in Defenses

| Decline Vector | Reviewer Skepticism | Wikimaker Preemptive Defense |
| :--- | :--- | :--- |
| **1. Team / Institutional Credit**<br>([WP:NOTINHERITED](https://en.wikipedia.org/wiki/Wikipedia:Notability_is_not_inherited)) | *"Breakthroughs belong to the research institute or team, not automatically to the individual scientist."* | • Pinpoint **Principal Investigator (PI)** or Project Lead appointments in citations.<br>• Anchor awards that specifically name the subject (e.g. *Nanaji Deshmukh Interdisciplinary Team Award* citation).<br>• Cite first-author and corresponding-author peer-reviewed publications (*Nature Scientific Reports*, *Theriogenology*). |
| **2. Syndicated Press Wires**<br>([WP:ORIGINAL](https://en.wikipedia.org/wiki/Wikipedia:Identifying_reliable_sources#News_organizations)) | *"Multiple news links are just wire reprints (PTI/IANS) of the same institutional press release."* | • Prioritize **distinct, original investigative journalism** (*The Hindu*, *The Tribune*, *Amar Ujala*, *Dainik Bhaskar*, *Moneycontrol*).<br>• Treat duplicate wire reprints as a single editorial origin. |
| **3. High Citation Bar on WP:PROF**<br>([WP:PROF](https://en.wikipedia.org/wiki/Wikipedia:Notability_(academics))) | *"Subject's raw h-index/citations may be modest compared to theoretical molecular biology."* | • Anchor the profile to **WP:PROF Criterion 7** (*Substantial impact outside academia*: 14,000 semen doses distributed, 300–600L lactation yield increase, multi-state rural deployment).<br>• Anchor to **WP:PROF Criterion 2** (*Major national awards & records*: Limca Book of Records, ICAR Nanaji Deshmukh Award, SAPI Fellowship). |
| **4. Over-reliance on Primary Sources**<br>([WP:BLPPRIMARY](https://en.wikipedia.org/wiki/Wikipedia:Biographies_of_living_persons#Reliable_sources)) | *"Too many claims cite employer PDFs, annual reports, or university directories."* | • Automated QA rules flag `institutional_bio` citations on achievement and award claims.<br>• Systematically replace institutional press releases with direct independent news reports. |
| **5. Resume / Promotional Tone**<br>([WP:NOTRESUME](https://en.wikipedia.org/wiki/Wikipedia:What_Wikipedia_is_not#Wikipedia_is_not_a_resume)) | *"Article lists routine workshops, training compendiums, or reads like an institutional CV."* | • Strip bureaucratic committees and routine training compendiums.<br>• Group statements chronologically into standard Wikipedia section taxonomy: *Education*, *Career*, *Research*, *Selected publications*, *Awards and recognition*. |

---

## 2. Multi-Sourcing Strategy (1 vs 2–3 Sources per Claim)

Wikimaker enforces a balanced citation density to satisfy [WP:EXTRAORDINARY](https://en.wikipedia.org/wiki/Wikipedia:Verifiability#Exceptional_claims_require_exceptional_sources) while avoiding [WP:OVERCITE](https://en.wikipedia.org/wiki/Wikipedia:Citation_overkill):

1. **Exceptional / Breakthrough Claims (2–3 Sources)**:
   - Major scientific firsts (e.g. *Hisar Gaurav* cloning, *Sach-Gaurav* field birth) → cite **1 independent national news outlet + 1 regional investigative report + 1 peer-reviewed journal DOI**.
   - National records (e.g. *Limca Book of Records*) → cite **1 independent newspaper feature + 1 registry record**.
2. **Routine Biographical Facts (1 Source)**:
   - Birthplace, district, university degrees, retirement date → **1 authoritative/reliable secondary source** (avoiding citation overkill).

---

## 3. Deduplication & Prose Neutrality Engine

1. **Claim Deduplication**:
   - The QA linter (`_check_duplicate_claims` in `wiki/draft_qa.py`) compares semantic tokens across all approved claims to prevent redundant phrasing of the same factual event.
2. **Attribution Chain Elimination**:
   - Strips meta-journalistic prefixes (*"The Hindu reported that..."*, *"India.com stated that..."*) and converts them into direct factual assertions backed by citation tags at sentence endings ([WP:NPOV](https://en.wikipedia.org/wiki/Wikipedia:Neutral_point_of_view)).

---

## 4. Multilingual & Regional Source Integration ([WP:NONENG](https://en.wikipedia.org/wiki/Wikipedia:Verifiability#Non-English_sources))

- Non-English secondary sources (e.g. *Amar Ujala*, *Dainik Bhaskar*, *City Tehelka*) are fully valid under Wikipedia policy when covering localized regional milestones (such as rural breeding impacts, village origins, or regional retirement events).
- Bilingual search expansion ensures query formulations run simultaneously in English and native scripts (Devanagari, French, German, Spanish) so regional investigative reports are captured during research.

---

## 5. Automated QA Linter Rule Summary (`wiki/draft_qa.py`)

| Rule ID | Severity | Purpose |
| :--- | :---: | :--- |
| `short_description` | Error | Requires `{{Short description|...}}` at top of draft |
| `infobox` | Error | Requires standard `{{Infobox ...}}` |
| `reflist` | Error | Requires `{{reflist}}` for references to render |
| `few_refs` | Error | Flags drafts with fewer than 10 references |
| `dirty_title` | Error | Detects truncated or malformed citation titles |
| `iso_date` | Error | Enforces dmy dates over raw ISO formats in citations |
| `bare_url` | Error | Blocks unformatted bare URLs in prose |
| `thin_lead` | Warning | Requires 3+ sentences in the lead section |
| `attribution_chain` | Warning | Flags conversational attribution chains (*"X reported that..."*) |
| `missing_date` | Warning | Requires `\|date=` in all citation templates |
| `weak_source` | Warning | Flags self-published or unreliable sources |
| `duplicate_approved_claim` | Warning | Detects duplicate approved claims asserting the same fact |
| `institutional_achievement_source` | Warning | Flags awards/achievements citing employer/institutional PDFs |
| `authority_control` | Warning | Requires `{{Authority control}}` |
| `defaultsort` | Warning | Requires `{{DEFAULTSORT:Last, First}}` |
| `categories` | Warning | Requires standard category links |
| `no_image` | Info | Advisory note if infobox lacks a portrait image |
