"""Generate wikitext draft for a saved session. Run with real ANTHROPIC_API_KEY set."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
sys.path.insert(0, os.path.dirname(__file__))

from engine.models import PersonProfile
from engine.llm import get_provider
from wiki.wikitext import render_en, render_hi

session_file = sys.argv[1] if len(sys.argv) > 1 else "prem_yadav_session.json"
hindi = "--hindi" in sys.argv

data = json.load(open(session_file))
profile = PersonProfile(**data["profile"])

print(f"Generating draft for: {profile.name}")
print(f"Notability: {profile.notability.label if profile.notability else 'unknown'}")
print(f"Sources: {len(profile.sources)} | Claims: {len(profile.claims)}")
print("-" * 60)

llm = get_provider()

wikitext = render_en(profile, llm)
profile.wikitext_en = wikitext

out_en = f"{profile.name.replace(' ', '_')}_draft_en.wiki"
with open(out_en, "w") as f:
    f.write(wikitext)
print(f"\nEnglish draft saved to: {out_en}")

if hindi:
    wikitext_hi = render_hi(profile, llm)
    profile.wikitext_hi = wikitext_hi
    out_hi = f"{profile.name.replace(' ', '_')}_draft_hi.wiki"
    with open(out_hi, "w") as f:
        f.write(wikitext_hi)
    print(f"Hindi draft saved to: {out_hi}")

# Save updated session with wikitext
data["profile"] = json.loads(profile.model_dump_json())
json.dump(data, open(session_file, "w"), indent=2)

print("\n--- ENGLISH DRAFT PREVIEW ---\n")
print(wikitext[:2000])
print("\n[...truncated, see full file...]" if len(wikitext) > 2000 else "")
