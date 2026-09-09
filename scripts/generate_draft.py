"""Generate a deterministic, evidence-grounded AfC draft from a saved session."""
import sys
import os
import json
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(root_dir, "backend"))
sys.path.insert(0, root_dir)

from engine.models import PersonProfile  # noqa: E402
from wiki.draft import audit_profile, render_draft  # noqa: E402

session_file = sys.argv[1] if len(sys.argv) > 1 else "prem_yadav_session.json"

data = json.load(open(session_file))
profile = PersonProfile(**data["profile"])

print(f"Generating draft for: {profile.name}")
print(f"Sources: {len(profile.sources)} | Claims: {len(profile.claims)}")
print("-" * 60)

audit = audit_profile(profile)
if not audit.ready:
    for issue in audit.blockers:
        print(f"BLOCKER: {issue.message}")
    sys.exit(1)
for issue in audit.warnings:
    print(f"WARNING: {issue.message}")

wikitext = render_draft(profile, audit)
profile.wikitext_en = wikitext
profile.wikitext_hi = None

out_en = f"{profile.name.replace(' ', '_')}_draft_en.wiki"
with open(out_en, "w") as f:
    f.write(wikitext)
print(f"\nEnglish draft saved to: {out_en}")

data["profile"] = json.loads(profile.model_dump_json())
json.dump(data, open(session_file, "w"), indent=2)

print("\n--- ENGLISH DRAFT PREVIEW ---\n")
print(wikitext[:2000])
print("\n[...truncated, see full file...]" if len(wikitext) > 2000 else "")
