"""A Scrapy interface to Jev, TypeSafe AI's System One model.

The package provides :class:`scrapy_jev.QualityGatePipeline`, a Scrapy item
pipeline that samples a bounded batch of scraped items, asks Jev how plausible
a configured set of fields looks, and stops the crawl when the pass rate drops
below a threshold.

Configure it in ``settings.py``::

    ITEM_PIPELINES = {"scrapy_jev.QualityGatePipeline": 400}
    OPENROUTER_API_KEY = "..."           # or JEV_API_KEY, or the env var
    JEV_FIELDS = ["name", "price", "sku", "category"]
"""

from .addon import Addon
from .client import JevClient
from .pipeline import QualityGatePipeline

__all__ = ["Addon", "JevClient", "QualityGatePipeline"]
__version__ = "0.1.0"