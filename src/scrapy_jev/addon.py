"""A Scrapy add-on that auto-registers the Jev quality-gate pipeline.

Adding the add-on to :setting:`ADDONS` removes the need to edit
``ITEM_PIPELINES`` by hand::

    ADDONS = {"scrapy_jev.Addon": 350}

``update_settings`` registers :class:`scrapy_jev.QualityGatePipeline` at
``JEV_PIPELINE_PRIORITY`` (default 400) unless it is already listed in
``ITEM_PIPELINES``. If ``JEV_FIELDS`` is empty or no API key is available the
add-on disables itself, so installing the package has no effect until it is
actually configured.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from scrapy.exceptions import NotConfigured

from .pipeline import QualityGatePipeline

if TYPE_CHECKING:
    from scrapy.crawler import Crawler
    from scrapy.settings import Settings

logger = logging.getLogger(__name__)

#: Priority used when the add-on adds the pipeline to ``ITEM_PIPELINES``.
DEFAULT_PIPELINE_PRIORITY = 400


class Addon:
    def __init__(self, crawler: Crawler) -> None:
        self.crawler = crawler

    @classmethod
    def from_crawler(cls, crawler: Crawler) -> Addon:
        return cls(crawler)

    def update_settings(self, settings: Settings) -> None:
        fields = settings.getlist("JEV_FIELDS", [])
        if not fields:
            raise NotConfigured(
                "JEV_FIELDS is empty, so the Jev quality gate is disabled"
            )

        api_key = (
            settings.get("JEV_API_KEY")
            or settings.get("OPENROUTER_API_KEY")
            or os.environ.get("JEV_API_KEY")
            or os.environ.get("OPENROUTER_API_KEY")
        )
        if not api_key:
            raise NotConfigured(
                "No API key found; set JEV_API_KEY or OPENROUTER_API_KEY"
            )

        settings.setdefault_in_component_priority_dict(
            "ITEM_PIPELINES", QualityGatePipeline, DEFAULT_PIPELINE_PRIORITY
        )