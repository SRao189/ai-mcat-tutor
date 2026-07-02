#!/usr/bin/env python3
"""Run one Phase 1 Council tutor request without printing secrets."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from council.config import CouncilConfig  # noqa: E402
from council.phase1 import answer_question  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Phase 1 NVIDIA Council tutor.")
    parser.add_argument("question")
    args = parser.parse_args()

    config = CouncilConfig.from_env(REPO)
    response = answer_question(args.question, config=config)
    print(json.dumps(response.to_dict(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
