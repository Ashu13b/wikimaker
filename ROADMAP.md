# ROADMAP

## Shipped
- Initial local person-research workflow with source collection, claim review,
  session persistence, and English/Hindi wikitext generation.

- Source-grounded deterministic draft pipeline with explicit claim approval,
  evidence diagnostics, server-owned generation, persistence, and a regression
  fixture that produces the Dr. Prem Singh Yadav draft without CV citations.

- Retired the legacy LLM/stub draft path (wiki/wikitext.py, StubProvider._draft):
  all drafting now goes through the audited deterministic renderer, so no code
  path can emit unverified or invented biography text.

## Next
- Finish and verify subject-first onboarding and Wikimedia-status routing.
- Add existing-article comparison and structured improvement suggestions.
- Introduce stable subject/session IDs so same-named people cannot collide.
- Strengthen claim-level provenance and separate authored works from independent
  notability evidence throughout scoring and drafting.
- Expand automated coverage for identity conflicts, source verification, and
  session migration.

- Replace the conservative hard-coded independent-news domain policy with a
  maintainable source-review registry and per-source editorial overrides.
- Add structured editorial controls for rewriting approved draft paraphrases in
  the UI; current approval uses the reviewed claim text.
## Out of scope
- Requiring a pre-existing Wikipedia article or Wikidata item before research.
- Automatically generating a competing draft when an article already exists.
