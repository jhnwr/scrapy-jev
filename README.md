# scrapy-jev

A Scrapy item pipeline that uses [Jev](https://typesafe.ai/) (TypeSafe AI's
System One model) to spot-check scraped fields and stop a crawl when the data
stops looking real.

Scraping silently degrades: a selector drifts to a new class name and fields
start coming back empty or wrong long before anyone notices. This pipeline
samples a bounded batch of items, asks Jev how plausible each of a few core
fields looks, and halts the spider when the pass rate drops below a threshold.

## Install

```sh
uv add scrapy-jev
```

## Configure

**Recommended: use the add-on.** One line auto-registers the pipeline, so you
never touch `ITEM_PIPELINES`:

```python
ADDONS = {
    "scrapy_jev.Addon": 350,
}

OPENROUTER_API_KEY = "..."   # or JEV_API_KEY; either may live in the env instead

JEV_FIELDS = ["name", "price", "sku", "category"]
```

If you prefer to wire the pipeline yourself (or need a different priority),
skip the add-on and list it directly:

```python
ITEM_PIPELINES = {
    "scrapy_jev.QualityGatePipeline": 400,
}
```

The first `JEV_SAMPLE_SIZE` items that carry any of `JEV_FIELDS` are judged, and
if fewer than `JEV_PASS_RATE_THRESHOLD` pass, the spider stops.

Installing the package with no `JEV_FIELDS` and no API key has no effect — the
add-on (and the pipeline) disable themselves until you configure them.

## Settings

| Setting                    | Default            | Meaning                                              |
| -------------------------- | ------------------ | ---------------------------------------------------- |
| `JEV_FIELDS`               | `[]`               | Fields to judge on each item.                        |
| `JEV_SAMPLE_SIZE`          | `20`               | Items to judge before deciding.                      |
| `JEV_PASS_RATE_THRESHOLD`  | `0.7`              | Minimum share (0–1) of items that must pass.         |
| `JEV_FIELD_THRESHOLD`      | `0.5`              | Per-field plausibility below which a field fails.    |
| `JEV_MODEL`                | `~typesafe/jev-latest` | Model id passed to the decisions endpoint.       |
| `JEV_BASE_URL`             | `https://openrouter.ai/api/alpha/decisions` | Endpoint.      |
| `JEV_PIPELINE_PRIORITY`    | `400`              | ITEM_PIPELINES priority used by the add-on.      |
| `JEV_API_KEY` / `OPENROUTER_API_KEY` | —        | API key (setting or env var).                        |
| `JEV_STOP_REASON`          | `"Extraction quality fell below threshold (Jev plausibility check)"` | Closing reason. |

## How it works

- An item is **judged** only if it declares at least one of `JEV_FIELDS`; other
  items (e.g. list pages) pass through untouched.
- Per item, Jev returns a 0–1 score per field. An item **passes** only when
  every field scores at or above `JEV_FIELD_THRESHOLD`. A field that comes back
  empty (`None`) is a failure, not a skip — that's the classic "selector
  drifted and returns nothing" break.
- After `JEV_SAMPLE_SIZE` items, if the passed share is below
  `JEV_PASS_RATE_THRESHOLD`, the spider is stopped.