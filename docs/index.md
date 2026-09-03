---
title: Sitemap
description: Multilingual XML sitemap and robots.txt generator for the Volkanos PWA stack.
sidebar:
  label: Overview
  collapsed: true
---

django-sitemap generates XML sitemaps and `robots.txt` per channel-domain. It runs as a management command (no HTTP endpoints), reads data from PIM (products, categories), ContentDB (pages, blog posts), and FAQ (Q&A items), and writes a directory of sitemap files plus a `robots.txt` that auto-references them.

## What It Does

- Generates per-content-type sitemap files (products, categories, custom products, ContentDB pages, FAQ items)
- Builds a `robots.txt` per channel-domain with automatic sitemap entries
- Multilingual output — one URL per (item, channel language) with optional merging into a single file
- URL prefix templates with `{{language_iso2}}` and `{{channel_short_idx}}` placeholders
- Soft-imports optional dependencies — generators skip themselves when their source module is absent

## Architecture

```
manage.py generate_sitemap --domain_idx <idx>
  → SitemapCoordinator (one per DomainSitemap)
    → ProductSitemapGenerator   (needs django-pim)
    → CategorySitemapGenerator  (needs django-pim)
    → ContentDBSitemapGenerator (needs django-contentdb)
    → FaqSitemapGenerator       (needs django-faq)
    → RobotsTxtGenerator        (auto-picks all *.xml in output dir)
```

Each generator writes to a temporary directory, then the coordinator atomically renames it to the final location. Output paths under `MEDIA_ROOT/sitemap/{domain_idx}/`.

## Data Model

| Entity | Purpose |
|---|---|
| `Channel` | Maps channel idx (e.g. `default-europe`) referenced by `DomainSitemap` |
| `DomainSitemap` | Per-domain config: `domain_url`, `languages` M2M, FK to `Channel` + `LanguageSitemap` |
| `LanguageSitemap` | Per-language URL prefixes (`product_url`, `category_url`, `custom_product_url`, `faq_url`), ContentDB content types JSON, exclusions, merge flag, custom robots.txt |

## URL Prefix Placeholders

URL templates support:

- `{{language_iso2}}` — language code (`en`, `pl`)
- `{{language_iso2.lower()}}` / `{{language_iso2.upper()}}` — case modifiers
- `{{channel_short_idx}}` — short channel idx (e.g. `eu`)

Example `faq_url`:

```
{{language_iso2.lower()}}/faq
```

Produces URLs like `https://example.com/en/faq/{url_key}` and `https://example.com/pl/faq/{url_key}`.

`LanguageSitemap.save()` strips leading/trailing slashes from all URL fields, so `/foo/faq/` and `foo/faq` are stored identically.

## Soft Dependencies

Each generator probes for its data source at import time. When the source is missing, the generator becomes a no-op and the rest of the pipeline continues.

| Source | Generator | Skip when |
|---|---|---|
| `django-pim` | products, categories | not installed |
| `django-contentdb` (or legacy `contentdb`) | ContentDB pages | not installed, or `contentdb_content_types_to_process` empty |
| `django-faq` | FAQ items | not installed, or `LanguageSitemap.faq_url` empty |

## Commands

```bash
python manage.py generate_sitemap --domain_idx <idx>        # full pipeline (default)
python manage.py generate_sitemap --domain_idx <idx> --sitemap    # only XML files
python manage.py generate_sitemap --domain_idx <idx> --robots     # only robots.txt
```

Runs for all `DomainSitemap` entries when `--domain_idx` is omitted.

## Configuration

```python
SITEMAP_URL_HOST = "https://shop.example.com"   # optional; per-domain URL comes from DomainSitemap
SITEMAP_FORMAT_XML = True                       # pretty-print XML output
SITEMAP_LIMIT = 2000                            # max URLs per sitemap file
SITEMAP_ROOT_DIR = MEDIA_ROOT                   # output root
LIST_OF_CATEGORY_IDXES_WHICH_ARE_EXCLUDED = []

# optional: custom robots.txt template, defaults to the one shipped with the app
SITEMAP_ROBOTS_TEMPLATE_PATH = "/etc/sitemap/robots.txt"
```

Output goes to `{SITEMAP_ROOT_DIR}/sitemap/{domain_idx}/`. A staging directory `{SITEMAP_ROOT_DIR}/sitemap-processing/{domain_idx}/` holds files mid-generation and is renamed atomically on success.

## Gotchas

- `LanguageSitemap.channel_short_idx` is unique globally, not per-channel. Two channels cannot share the same short idx.
- URL placeholders are string-substituted, not evaluated. Unknown placeholders pass through unchanged and produce broken URLs.
- `exclude_product_types` uses magic integer codes from PIM's `ProductType` enum (0=Base, 1=Simple, 2=Configurable, 3=Bundle, 4=Custom). Keep in sync when PIM adds new types.
- `merge_languages_in_sitemap=True` produces one file per channel with all languages inside. `False` produces one file per (channel, language) pair — useful when languages live on different subdomains.
- `robots_txt` field on `LanguageSitemap` overrides the default template, but sitemap `Sitemap: …` entries are still appended automatically by `RobotsTxtGenerator`. The template itself holds directives only (`User-agent`, `Allow`, `Disallow`).
- The legacy `tests.py` placeholder is empty. Real tests live under `tests/` (since 3.2.0).
