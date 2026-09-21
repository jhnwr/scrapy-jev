# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-09-21

Initial release.

### Added

- `scrapy_jev.QualityGatePipeline` — samples `JEV_SAMPLE_SIZE` items, asks Jev
  how plausible each configured field looks, and stops the spider when the
  pass rate drops below `JEV_PASS_RATE_THRESHOLD`.
- `scrapy_jev.JevClient` — batched client for OpenRouter's
  `/api/alpha/decisions` endpoint (`~typesafe/jev-latest`).
- `scrapy_jev.Addon` — Scrapy add-on that auto-registers the pipeline.
- `JEV_*` settings for configuration; works with Scrapy `Item`, dict, attrs,
  and dataclass items via `itemadapter`.

[0.1.0]: https://github.com/jhnwr/scrapy-jev/releases/tag/v0.1.0