#!/usr/bin/env python3
"""Mobile-friendly response pager for Termux and SSH sessions."""
import json
import subprocess
import sys
from pathlib import Path

def main():
    conv_id = "51f9320e-9811-416e-a7d3-32f231566291"
    log_path = Path(f"/home/ubuntu/.gemini/antigravity-cli/brain/{conv_id}/.system_generated/logs/transcript.jsonl")
    
    if not log_path.exists():
        print("No conversation transcript found.")
        return

    lines = [json.loads(line) for line in log_path.read_text().splitlines() if line.strip()]
    responses = [entry for entry in lines if entry.get("type") == "PLANNER_RESPONSE" and entry.get("content")]
    
    if not responses:
        print("No assistant responses found yet.")
        return

    idx = -1
    if len(sys.argv) > 1:
        try:
            idx = int(sys.argv[1])
        except ValueError:
            pass

    content = responses[idx].get("content", "")
    
    if sys.stdout.isatty():
        proc = subprocess.Popen(
            ["less", "-R", "-P", "--- Termux Scroll View (Swipe/Arrows to scroll | 'q' to exit) ---"],
            stdin=subprocess.PIPE,
            text=True
        )
        proc.communicate(input=content)
    else:
        print(content)

if __name__ == "__main__":
    main()
