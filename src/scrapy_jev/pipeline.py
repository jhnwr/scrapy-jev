"""Quality-gate pipeline: halt a crawl when scraped fields stop looking real.

Scraping silently degrades: a selector drifts to a new class name and fields
start coming back empty or wrong long before anyone notices. This pipeline
samples a bounded batch of items, asks Jev how plausible each of a few core
fields looks, and stops the spider when the pass rate drops below a threshold.

The check is a *sample*, not a census: ``JEV_SAMPLE_SIZE`` items are judged,
their pass rate is compared against ``JEV_PASS_RATE_THRESHOLD``, and the spider
is stopped on failure. Sampling keeps Jev spend bounded and independent of
crawl size.

The stop is done by asking the engine to close, *not* by raising
``CloseSpider``: Scrapy's item-processing path swallows ``CloseSpider`` (it
subclasses ``Exception`` and is caught by the item-error handler), so raising
it would only log an item error and keep crawling.
"""

from __future__ import annotations

import logging
import os
from typing import Callable

from itemadapter import ItemAdapter
from scrapy.utils.defer import deferred_from_coro

from .client import JevClient

logger = logging.getLogger(__name__)

#: Default stop message when the pass rate falls below threshold.
DEFAULT_STOP_REASON = (
    "Extraction quality fell below threshold (Jev plausibility check)"
)


class QualityGatePipeline:
    """Spot-check extracted fields with Jev and stop the spider on bad data.

    Items that do not carry any of ``fields`` (for example list-page items in
    a crawl that mixes page types) are passed through unchecked.
    """

    def __init__(
        self,
        client: JevClient,
        fields: list[str],
        sample_size: int,
        pass_rate_threshold: float,
        field_threshold: float,
        stop_reason: str,
        stop: "Callable[[str], None] | None" = None,
        enabled: bool = True,
    ) -> None:
        self.client = client
        self.fields = fields
        self.sample_size = sample_size
        self.pass_rate_threshold = pass_rate_threshold
        self.field_threshold = field_threshold
        self.stop_reason = stop_reason
        self._stop = stop
        self.enabled = enabled
        self.scored = 0
        self.passed = 0

    @classmethod
    def from_crawler(cls, crawler):
        settings = crawler.settings
        api_key = settings.get("JEV_API_KEY") or settings.get("OPENROUTER_API_KEY")
        if not api_key:
            api_key = os.environ.get("JEV_API_KEY") or os.environ.get(
                "OPENROUTER_API_KEY"
            )
        fields = settings.getlist("JEV_FIELDS", [])

        enabled = bool(fields) and bool(api_key)
        if not enabled:
            missing = []
            if not fields:
                missing.append("JEV_FIELDS")
            if not api_key:
                missing.append("JEV_API_KEY or OPENROUTER_API_KEY")
            logger.warning(
                "scrapy_jev: gate disabled, missing %s", " and ".join(missing)
            )

        def stop(reason: str) -> None:
            deferred = deferred_from_coro(
                crawler.engine.close_spider_async(reason=reason)
            )
            deferred.addErrback(
                lambda failure: logger.error(
                    "scrapy_jev: failed to schedule spider close: %s", failure
                )
            )

        return cls(
            client=JevClient(
                api_key=api_key or "",
                model=settings.get("JEV_MODEL", "~typesafe/jev-latest"),
                base_url=settings.get(
                    "JEV_BASE_URL", "https://openrouter.ai/api/alpha/decisions"
                ),
            ),
            fields=fields,
            sample_size=settings.getint("JEV_SAMPLE_SIZE", 20),
            pass_rate_threshold=settings.getfloat("JEV_PASS_RATE_THRESHOLD", 0.7),
            field_threshold=settings.getfloat("JEV_FIELD_THRESHOLD", 0.5),
            stop_reason=settings.get("JEV_STOP_REASON", DEFAULT_STOP_REASON),
            stop=stop,
            enabled=enabled,
        )

    def _close(self, reason: str) -> None:
        if self._stop is not None:
            self._stop(reason)
        else:
            logger.error("scrapy_jev: would stop spider (no engine attached): %s", reason)

    def _item_passed(self, scores: dict[str, float]) -> bool:
        """Return True only when every configured field clears the threshold.

        A missing field (``None``) is a failure too: the configured fields are
        the ones that must always be scraped, so a selector drifting to return
        nothing is the most common breakage and must stop the crawl.
        """
        return all(
            score is not None and score >= self.field_threshold
            for score in scores.values()
        )

    def process_item(self, item):
        if not self.enabled:
            return item
        if not ItemAdapter.is_item(item):
            return item

        adapter = ItemAdapter(item)
        if set(adapter.field_names()).isdisjoint(self.fields):
            return item

        if self.scored >= self.sample_size:
            return item

        scores = self.client.score_item(item, self.fields)
        self.scored += 1
        if self._item_passed(scores):
            self.passed += 1
        else:
            failures = [
                f"{field}={scores[field]!r}"
                for field in self.fields
                if scores.get(field) is None or scores.get(field) < self.field_threshold
            ]
            logger.warning("scrapy_jev: item failed quality check: %s", ", ".join(failures))

        if self.scored >= self.sample_size:
            pass_rate = self.passed / self.sample_size
            if pass_rate < self.pass_rate_threshold:
                reason = (
                    f"{self.stop_reason}: {self.passed}/{self.sample_size} "
                    f"items passed ({pass_rate:.0%} < {self.pass_rate_threshold:.0%})"
                )
                logger.error("scrapy_jev: stopping spider: %s", reason)
                self._close(reason)
        return item