"""Jev client: decide whether a scraped field value "looks like" real data.

Jev is a System One model from TypeSafe AI. It answers narrow, typed
*questions* about a piece of *state* and returns calibrated probabilities
rather than generated text. This module wraps the OpenRouter alpha endpoint
that fronts Jev so we can ask it "does this look like a product name?" and get
a number back.

The ``score`` question type rates the state against ordered levels and returns
a ``score`` (probability-weighted level index) plus ``confidence``. For our
purposes we use a two-level scale — "does not look like a <field>" (0) to
"looks like a <field>" (1) — so the returned ``score`` *is* the probability
that the value is correct.
"""

from __future__ import annotations

import logging
from typing import Any

import requests
from itemadapter import ItemAdapter

logger = logging.getLogger(__name__)

# Score levels for "is this field value plausible". The returned `score` on a
# two-level scale (0..1) is exactly P(plausible), which is what we threshold.
PLAUSIBILITY_LEVELS = [
    "Does not look like a real value for this field",
    "Looks like a plausible, correctly-scraped value for this field",
]


class JevClient:
    """Thin client for the OpenRouter ``/api/alpha/decisions`` endpoint.

    Jev evaluates many questions against one ``state`` in a single request, so
    ``score_item`` sends the whole item as the state and asks one question per
    field. This is faster and cheaper than one request per field.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "~typesafe/jev-latest",
        base_url: str = "https://openrouter.ai/api/alpha/decisions",
        timeout: float = 60.0,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.timeout = timeout

    def score_item(self, item: Any, fields: list[str]) -> dict[str, float | None]:
        """Score every field of ``item`` in a single Jev request.

        ``item`` may be any item type understood by ``itemadapter`` (a Scrapy
        ``Item``, a dict, an attrs instance, or a dataclass). The parsed fields
        are sent together as the ``state``; each field is a separate ``score``
        question whose ``instructions`` names that field in ``state``.

        Returns a dict of field -> score (0..1), where a field is ``None`` when
        it is empty/absent and there is nothing to judge.
        """
        adapter = ItemAdapter(item)
        values: dict[str, str] = {}
        for field in fields:
            value = adapter.get(field)
            if value is None:
                continue
            text = value.strip() if isinstance(value, str) else str(value)
            if text:
                values[field] = text

        if not values:
            return {field: None for field in fields}

        questions = {
            field: {
                "type": "score",
                "instructions": {
                    "field": field,
                    "value": text,
                    "question": (
                        f"Is the value of `field` a plausible, correctly-scraped"
                        f" value for a {field}?"
                    ),
                },
                "criteria": PLAUSIBILITY_LEVELS,
            }
            for field, text in values.items()
        }

        response = requests.post(
            self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "state": {"field_values": values},
                "questions": questions,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        answers = data["answers"]
        logger.info("Jev response: %s", data)

        results: dict[str, float | None] = {}
        for field in fields:
            if field not in values:
                results[field] = None
                continue
            results[field] = float(answers[field]["score"])
        return results

    def __repr__(self) -> str:  # keep logs concise
        return f"<JevClient model={self.model!r}>"