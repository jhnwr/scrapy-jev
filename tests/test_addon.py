import pytest
from scrapy.exceptions import NotConfigured
from scrapy.settings import Settings

from scrapy_jev import Addon
from scrapy_jev.pipeline import QualityGatePipeline


class _Crawler:
    """Minimal stand-in; the addon's update_settings never touches crawler."""


def test_addon_registers_pipeline(monkeypatch):
    monkeypatch.delenv("JEV_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    settings = Settings()
    settings.set("JEV_FIELDS", ["name", "price"])
    settings.set("ITEM_PIPELINES", {})
    Addon(_Crawler()).update_settings(settings)
    assert settings.getdict("ITEM_PIPELINES")[QualityGatePipeline] == 400


def test_addon_does_not_override_existing_pipeline(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    settings = Settings()
    settings.set("JEV_FIELDS", ["name"])
    settings.set("ITEM_PIPELINES", {QualityGatePipeline: 123})
    Addon(_Crawler()).update_settings(settings)
    assert settings.getdict("ITEM_PIPELINES")[QualityGatePipeline] == 123


def test_addon_disabled_without_fields(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    settings = Settings()
    settings.set("JEV_FIELDS", [])
    with pytest.raises(NotConfigured):
        Addon(_Crawler()).update_settings(settings)


def test_addon_disabled_without_key(monkeypatch):
    monkeypatch.delenv("JEV_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    settings = Settings()
    settings.set("JEV_FIELDS", ["name"])
    with pytest.raises(NotConfigured):
        Addon(_Crawler()).update_settings(settings)