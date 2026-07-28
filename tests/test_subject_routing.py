from unittest import TestCase
from unittest.mock import patch

from engine.identifier import fetch_wikidata_photo_by_id
from wiki.wiki_check import check_existing_page, draft_generation_allowed


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
