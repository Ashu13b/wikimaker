from engine.models import Claim, PersonProfile, Source
from engine.saturation import (
    calculate_claim_similarity,
    cluster_claims,
    analyze_research_saturation,
)


def test_claim_similarity_matching_and_different_years():
    c1 = Claim(text="Produced Hisar Gaurav, a cloned Murrah buffalo bull in 2015", field="known_for")
    c2 = Claim(text="CIRB scientists cloned Hisar Gaurav Murrah bull in 2015", field="known_for")
    c3 = Claim(text="Produced seven clones of breeding bull M-29 in 2020", field="known_for")
    c4 = Claim(text="Born in village of Nimoth in Rewari district", field="birth_place")

    # c1 and c2 describe the same 2015 cloning event -> high similarity
    sim_1_2 = calculate_claim_similarity(c1, c2)
    assert sim_1_2 >= 0.55

    # c1 and c3 describe different events in different years (2015 vs 2020) -> low similarity
    sim_1_3 = calculate_claim_similarity(c1, c3)
    assert sim_1_3 < 0.40

    # c1 and c4 describe totally different facts
    sim_1_4 = calculate_claim_similarity(c1, c4)
    assert sim_1_4 < 0.20


def test_cluster_claims_and_corroboration():
    claims = [
        Claim(text="Cloned Hisar Gaurav in 2015", field="achievement", source_url="https://thehindu.com/1"),
        Claim(text="Produced Hisar Gaurav cloned buffalo in 2015", field="achievement", source_url="https://tribuneindia.com/2"),
        Claim(text="Cloned Hisar Gaurav bull in 2015", field="achievement", source_url="https://amarujala.com/3"),
        Claim(text="Received Nanaji Deshmukh ICAR award in 2019", field="award", source_url="https://icar.org.in/4"),
    ]

    clusters = cluster_claims(claims)
    # Should produce 2 clusters: the 2015 cloning milestone and the 2019 award
    assert len(clusters) == 2

    cloning_cluster = next(c for c in clusters if "Hisar Gaurav" in c.canonical_text)
    assert cloning_cluster.repetition_count == 3
    assert len(cloning_cluster.corroborating_sources) == 3
    assert set(cloning_cluster.claim_indices) == {0, 1, 2}

    award_cluster = next(c for c in clusters if "Nanaji Deshmukh" in c.canonical_text)
    assert award_cluster.repetition_count == 1
    assert len(award_cluster.corroborating_sources) == 1


def test_analyze_research_saturation():
    profile = PersonProfile(name="Test Scientist")
    profile.sources = [
        Source(url="https://thehindu.com/1", title="Title 1", publisher="The Hindu", editorial_origin="The Hindu", human_verified=True),
        Source(url="https://ndtv.com/2", title="Title 2", publisher="NDTV", editorial_origin="PTI", human_verified=True),
        Source(url="https://deccanherald.com/3", title="Title 3", publisher="Deccan Herald", editorial_origin="PTI", human_verified=True),
        Source(url="https://tribuneindia.com/4", title="Title 4", publisher="The Tribune", editorial_origin="The Tribune", human_verified=True),
        Source(url="https://amarujala.com/5", title="Title 5", publisher="Amar Ujala", editorial_origin="Amar Ujala", human_verified=True),
        Source(url="https://bhaskar.com/6", title="Title 6", publisher="Dainik Bhaskar", editorial_origin="Bhaskar", human_verified=True),
        Source(url="https://moneycontrol.com/7", title="Title 7", publisher="Moneycontrol", editorial_origin="PTI", human_verified=True),
        Source(url="https://zeenews.com/8", title="Title 8", publisher="Zee News", editorial_origin="Zee", human_verified=True),
        Source(url="https://etvbharat.com/9", title="Title 9", publisher="ETV Bharat", editorial_origin="ETV", human_verified=True),
        Source(url="https://kisantak.in/10", title="Title 10", publisher="Kisan Tak", editorial_origin="India Today", human_verified=True),
        Source(url="https://cirb.res.in/11", title="Title 11", publisher="CIRB", editorial_origin="CIRB", human_verified=True),
        Source(url="https://icar.org.in/12", title="Title 12", publisher="ICAR", editorial_origin="ICAR", human_verified=True),
    ]
    # 8 claims, 4 of which repeat the cloning milestone
    profile.claims = [
        Claim(text="Cloned Hisar Gaurav in 2015", field="achievement", source_url="https://thehindu.com/1"),
        Claim(text="Produced Hisar Gaurav cloned buffalo in 2015", field="achievement", source_url="https://tribuneindia.com/4"),
        Claim(text="Cloned Hisar Gaurav bull in 2015", field="achievement", source_url="https://amarujala.com/5"),
        Claim(text="Born in village of Nimoth in Rewari district", field="birth_place", source_url="https://amarujala.com/5"),
        Claim(text="Hails from Nimoth village in Rewari", field="birth_place", source_url="https://bhaskar.com/6"),
        Claim(text="Received Nanaji Deshmukh ICAR award in 2019", field="award", source_url="https://icar.org.in/12"),
        Claim(text="Produced seven clones of M-29 in 2020", field="achievement", source_url="https://moneycontrol.com/7"),
        Claim(text="Produced 7 clones of M-29 in 2020", field="achievement", source_url="https://zeenews.com/8"),
    ]
    profile.missing_slots = []

    sat = analyze_research_saturation(profile)

    assert sat.total_claims_analyzed == 8
    assert sat.unique_fact_count == 4  # 4 distinct fact clusters
    assert sat.repetition_rate == 0.50  # 50% repetition
    assert sat.syndication_rate > 0.0   # PTI wire repetition detected
    assert sat.score >= 0.70           # High saturation!
    assert sat.level in {"saturated", "mature"}
    assert len(sat.corroborated_clusters) >= 3
