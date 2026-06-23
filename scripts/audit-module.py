#!/usr/bin/env python3

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

CONTEXT = Path("wiki/course/context/module-1-context.md")
MODULE = Path("course-data/module-1.json")
OUTPUT = Path("validation/module-1-grounding-audit.md")

if not CONTEXT.exists():
    raise SystemExit(f"Missing: {CONTEXT}")

if not MODULE.exists():
    raise SystemExit(f"Missing: {MODULE}")

api_key = os.environ.get("NVIDIA_API_KEY")
if not api_key:
    env_file = Path.home() / ".config/mcat-litellm.env"

    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("NVIDIA_API_KEY="):
                api_key = line.split("=", 1)[1].strip()
                break

if not api_key:
    raise SystemExit("NVIDIA_API_KEY was not found.")

context = CONTEXT.read_text(encoding="utf-8-sig")
module = MODULE.read_text(encoding="utf-8-sig")

prompt = f"""
You are auditing an MCAT lesson against its sole allowed source.

SOURCE PACKET:
--- BEGIN SOURCE ---
{context}
--- END SOURCE ---

GENERATED MODULE:
--- BEGIN MODULE ---
{module}
--- END MODULE ---

Audit the module section by section.

For every unsupported or partially supported claim, report:

- JSON location
- Exact claim
- Status: unsupported or partially supported
- Why it is not fully supported
- Closest available source evidence
- Required correction

Rules:

- Use only the source packet.
- Do not add outside knowledge.
- Do not rewrite the module.
- Do not discuss claims that are fully supported.
- If every claim is supported, say exactly:
  ALL CLAIMS SUPPORTED
- Keep the report under 1,500 words.
"""

payload = {
    "model": "qwen/qwen3-next-80b-a3b-instruct",
    "messages": [
        {
            "role": "user",
            "content": prompt
        }
    ],
    "temperature": 0,
    "max_tokens": 2200,
    "stream": False
}

request = urllib.request.Request(
    "https://integrate.api.nvidia.com/v1/chat/completions",
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    },
    method="POST"
)

print("Starting direct grounding audit...")
started = time.perf_counter()

try:
    with urllib.request.urlopen(request, timeout=300) as response:
        result = json.loads(response.read().decode("utf-8"))
except Exception as exc:
    raise SystemExit(f"Audit request failed: {exc}") from exc

elapsed = time.perf_counter() - started
message = result["choices"][0]["message"]

audit = message.get("content", "").strip()

if not audit:
    audit = message.get("reasoning_content", "").strip()

if not audit:
    raise SystemExit("The model returned no audit text.")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(audit + "\n", encoding="utf-8")

print(f"Audit completed in {elapsed:.1f} seconds.")
print(f"Wrote: {OUTPUT}")
