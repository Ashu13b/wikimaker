from unittest import TestCase
from unittest.mock import patch

from engine.identifier import fetch_wikidata_photo_by_id
from wiki.wiki_check import check_existing_page, draft_generation_allowed


class IdentifyPreviewTests(TestCase):
    @patch("wiki.wiki_check.check_existing_page")
    @patch("engine.researcher._duckduckgo_html", return_value=None)
    @patch("engine.researcher._google_cse")
    @patch("engine.identifier.find_candidates")
    def test_identify_merges_identity_matches_and_web_clues(self, find_candidates, google_cse, _ddg, check_page):
        from engine.models import PersonCandidate, Source
        find_candidates.return_value = [PersonCandidate(
            name="Prem Singh Yadav (scientist)",
            photo_url="https://example.test/ps.jpg",
            bio_snippet="Indian buffalo cloning scientist",
            birth_year="1963",
            nationality="Indian",
            field="Animal biotechnology",
            affiliation="ICAR-CIRB",
            wikipedia_url="https://en.wikipedia.org/wiki/Prem_Singh_Yadav_(scientist)",
            wikidata_id="Q123456",
        )]
        google_cse.return_value = [Source(
            url="https://news.example.test/report",
            title="Buffalo cloning report",
            publisher="Example News",
            snippet="A cloned buffalo calf was born.",
        )]

        class _Clear:
            def model_dump(self):
                return {"status": "clear", "url": None, "note": None}
        check_page.return_value = _Clear()
        from backend.main import identify
        from backend.schemas import IdentifyRequest

        result = identify(IdentifyRequest(name="Prem Singh Yadav", field="biotech", affiliation="ICAR-CIRB"))

        identity = [r for r in result["results"] if r["kind"] == "identity"]
        web = [r for r in result["results"] if r["kind"] == "web"]
        self.assertEqual(len(identity), 1)
        self.assertEqual(identity[0]["wikidata_id"], "Q123456")
        self.assertEqual(identity[0]["wikipedia_url"], "https://en.wikipedia.org/wiki/Prem_Singh_Yadav_(scientist)")
        self.assertEqual(identity[0]["photo_url"], "https://example.test/ps.jpg")
        self.assertEqual(len(web), 1)
        self.assertEqual(web[0]["title"], "Buffalo cloning report")
        # The identity match's article title drives the routing check.
        check_page.assert_called_once_with("Prem Singh Yadav (scientist)")
        self.assertEqual(result["wiki_status"]["status"], "clear")


class ResearchStartRoutingTests(TestCase):
    @patch("backend.routes_research.fetch_institution_sources", return_value=[])
    @patch("backend.routes_research.fetch_auto_sources", return_value=([], None))
    @patch("backend.routes_research.check_existing_page")
    def test_confirmed_wikipedia_url_routes_by_article_title(self, check_page, _auto, _inst):
        class _WikiStatus:
            def model_dump(self):
                return {"status": "clear", "url": None, "note": None}

        check_page.return_value = _WikiStatus()
        from backend.main import research_start
        from backend.schemas import ResearchRequest

        research_start(ResearchRequest(
            name="Prem Singh Yadav",
            wikipedia_url="https://en.wikipedia.org/wiki/Prem_Singh_Yadav_(scientist)",
        ))

        check_page.assert_called_once_with("Prem Singh Yadav (scientist)")


class WikiStatusRoutingTests(TestCase):
    @patch("wiki.wiki_check._deletion_note")
    @patch("wiki.wiki_check._page_exists")
    def test_existing_article_takes_precedence(self, page_exists, deletion_note):
        page_exists.side_effect = lambda title: title == "Ada Example"

        status = check_existing_page("Ada Example")

        self.assertEqual(status.status, "exists")
        self.assertEqual(status.url, "https://en.wikipedia.org/wiki/Ada_Example")
        deletion_note.assert_not_called()

    @patch("wiki.wiki_check._deletion_note")
    @patch("wiki.wiki_check._page_exists")
    def test_existing_draft_routes_to_improvement(self, page_exists, deletion_note):
        page_exists.side_effect = lambda title: title == "Draft:Ada Example"

        status = check_existing_page("Ada Example")

        self.assertEqual(status.status, "draft")
        self.assertEqual(status.url, "https://en.wikipedia.org/wiki/Draft:Ada_Example")
        deletion_note.assert_not_called()

    @patch("wiki.wiki_check._deletion_note", return_value="delete on 2025-01-02")
    @patch("wiki.wiki_check._page_exists", return_value=False)
    def test_prior_deletion_routes_to_review(self, _page_exists, _deletion_note):
        status = check_existing_page("Ada Example")
        self.assertEqual(status.status, "deleted")

    def test_only_new_and_existing_draft_modes_can_generate_wikitext(self):
        self.assertTrue(draft_generation_allowed("clear"))
        self.assertTrue(draft_generation_allowed("draft"))
        self.assertFalse(draft_generation_allowed("exists"))
        self.assertFalse(draft_generation_allowed("deleted"))


class WikidataEnrichmentTests(TestCase):
    @patch("engine.identifier._wikidata_detail")
    def test_invalid_qid_never_triggers_enrichment(self, detail):
        self.assertIsNone(fetch_wikidata_photo_by_id("Ada Example"))
        detail.assert_not_called()

    @patch("engine.identifier._wikidata_detail", return_value={"photo_url": "https://example.test/ada.jpg"})
    def test_confirmed_qid_can_supply_photo(self, detail):
        self.assertEqual(
            fetch_wikidata_photo_by_id("Q123"),
            "https://example.test/ada.jpg",
        )
        detail.assert_called_once_with("Q123")
