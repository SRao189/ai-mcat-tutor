"""Small schema checks for core v2 contracts."""

from __future__ import annotations

import re
from typing import Any


CONCEPT_ID = re.compile(r"^[a-z0-9]+(\.[a-z0-9-]+)+$")
VERIFICATIONS = {"verified", "unsupported", "source-gap"}


def validate_wiki_concept_page(page: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in ("conceptId", "title", "summary", "claims", "equations", "examples", "figures", "relatedConcepts"):
        if field not in page:
            errors.append(f"missing required field: {field}")
    concept_id = str(page.get("conceptId", ""))
    if concept_id and not CONCEPT_ID.match(concept_id):
        errors.append("conceptId does not match dotted concept id pattern")
    claims = page.get("claims", [])
    if not isinstance(claims, list):
        errors.append("claims must be a list")
        return errors
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            errors.append(f"claims[{index}] must be an object")
            continue
        for field in ("text", "sourceId", "sourceSpan", "verification", "confidence"):
            if field not in claim:
                errors.append(f"claims[{index}] missing required field: {field}")
        if claim.get("verification") not in VERIFICATIONS:
            errors.append(f"claims[{index}] invalid verification")
        confidence = claim.get("confidence")
        if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            errors.append(f"claims[{index}] confidence must be between 0 and 1")
    return errors
