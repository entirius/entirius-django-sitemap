# AGENTS.md

Multilingual XML sitemap and robots.txt generator for Volkanos PWAs — distribution
`entirius-django-sitemap`, Django app `django_sitemap`. Produces separate sitemaps per content type (products, categories, custom products, ContentDB pages, FAQ items), a sitemap index, and a `robots.txt` per channel-domain. Supports language-scoped URL prefixes, alternate language links (hreflang), and optional language merging into a single file.

**Tech:** Python >=3.11, Django >=4.0, tqdm, pytz, entirius-py-process-logger,
entirius-django-regional. Soft integrations (extras): entirius-django-pim, entirius-django-contentdb,
entirius-django-faq.

## Commands

| Command | Meaning |
|---|---|
| `make install` | sync dependencies (uv, incl. extras) |
| `make check` | lint + format-check (ruff) |
| `make fix` | auto-fix lint + format |
| `make test` | test suite (pytest + pytest-django) |

## Conventions

- English only: code, docs, commits, branches, PRs.
- MPL-2.0: every non-trivial source file carries the license header (pre-commit inserts it).
- Toolchain: uv + ruff + hatchling + pytest; all config in `pyproject.toml`; `uv.lock` committed.
- Git flow: `master` (production) + `develop` (integration); changes land via PR; semver tag on `master`.
- Never rename the package / Django app_label / DB table prefix `django_sitemap` — it is a schema contract.
- Migrations are part of the public contract — never edit an already released migration.
- Default: do not commit — git is the user's call.

## Architecture

```
src/django_sitemap/
├── apps.py                          # DjangoSitemapConfig (is_volkanos = True)
├── settings.py                      # SITEMAP_* config + ContentDB import fallback (django_contentdb → contentdb)
├── admin.py
│
├── models/
│   ├── channel.py                   # LanguageSitemap — per-language URL prefixes, exclusions, robots.txt
│   ├── contentdb.py                 # ContentDBPage (abstract proxy — scoping query for ContentDB)
│   ├── faq.py                       # FaqPage (abstract proxy — scoping query for FAQ)
│   └── domain_sitemap.py            # Channel + DomainSitemap — maps channel idx to domain URL + languages
│
├── worker/
│   ├── sitemap.py                   # Entry points: generate_sitemap(domain_sitemap), generate_robots(...)
│   └── generators/
│       ├── base.py                  # BaseSitemapGenerator (abstract)
│       ├── product.py               # ProductSitemapGenerator
│       ├── category.py              # CategorySitemapGenerator
│       ├── contentdb.py             # ContentDBSitemapGenerator (skipped if ContentDB absent)
│       ├── faq.py                   # FaqSitemapGenerator (skipped if django-faq absent or faq_url empty)
│       ├── robots.py                # RobotsTxtGenerator
│       └── sitemap_coordinator.py   # SitemapCoordinator — orchestrates all generators + index
│
├── management/commands/
│   └── generate_sitemap.py          # python manage.py generate_sitemap {shop_idx} [--languages en de fr]
│
├── templates/admin/                 # sitemap.xml, robots.txt Django templates
└── migrations/
```

Generation flow: `generate_sitemap` management command iterates `DomainSitemap` rows for a given `shop_idx`, instantiates a `SitemapCoordinator` per domain, which runs each generator (product → category → custom-product → ContentDB → robots → index).

## Data Model

| Entity | Key Fields | Relationships |
|---|---|---|
| Channel | idx (unique) | Referenced by DomainSitemap |
| DomainSitemap | idx (unique), domain_url | FK → Channel, FK → LanguageSitemap, M2M → `django_regional.Language` |
| LanguageSitemap | idx, channel_short_idx (both unique), is_active, product_url, category_url, custom_product_url, faq_url, contentdb_content_types_to_process (JSON), contentdb_access_rights (JSON), merge_languages_in_sitemap, skip_category_without_enabled_products, exclude_product_types (JSON), robots_txt (custom override) | Back-reference from DomainSitemap |

URL prefix templates support placeholders:
- `{{language_iso2}}` — language ISO2 code (e.g. `en`, `pl`)
- `{{channel_short_idx}}` — short idx of the channel
- Modifiers: `{{language_iso2.lower()}}`, `{{language_iso2.upper()}}`

Example `contentdb_content_types_to_process`:
```json
{"blog-post": "{{language_iso2.lower()}}/porady", "static-page": "{{channel_short_idx}}/static"}
```

`exclude_product_types` uses integer codes: `0=ProductBase, 1=ProductSimple, 2=ProductConfigurable, 3=ProductBundle, 4=ProductCustom`.

`LanguageSitemap.save()` strips leading/trailing slashes from all `*_url` fields.

## Commands

```bash
python manage.py generate_sitemap {shop_idx}
python manage.py generate_sitemap {shop_idx} --languages en de fr
```

## Configuration

```python
SITEMAP_URL_HOST                         = "https://shop.example.com"   # trailing slash stripped
SITEMAP_FORMAT_XML                       = True
SITEMAP_LIMIT                            = 2000                          # max URLs per sitemap file
SITEMAP_ROOT_DIR                         = MEDIA_ROOT                    # output root
LIST_OF_CATEGORY_IDXES_WHICH_ARE_EXCLUDED = []
```

Output paths:
- `{SITEMAP_ROOT_DIR}/sitemap/` — final artefacts
- `{SITEMAP_ROOT_DIR}/sitemap-processing/` — temporary generation dir

## Dependencies

**Runtime:** Django >=4.0, tqdm, pytz, entirius-py-process-logger,
entirius-django-regional (`Language` — M2M on `DomainSitemap`).

**Soft dependencies (extras; detected at import in `settings.py` / generators):**
- `django_contentdb` (or legacy `contentdb`) — when neither is present, ContentDB sitemap generation is skipped and `CONTENTDB_PACKAGE = None`.
- `django_faq` — when not installed, FAQ sitemap generation is skipped and `FAQ_PACKAGE = None`. Also skipped at runtime when `LanguageSitemap.faq_url` is empty.
- `django_pim` — when not installed, product and category generators stop with a log message.

## Testing

Tests run on postgres via `DATABASE_URL` (CI provides a postgres service; locally point it at any
postgres 15+).

```bash
make install
make test
```

Test suite covers `LanguageSitemap.faq_url` normalization, `FaqPage.get_active_items` channel scoping (8 branches), and `FaqSitemapGenerator` end-to-end (guard paths, URL formatting, merged/per-language XML output).

## Gotchas

- `<lastmod>` source field differs per generator because upstream models do not share a base: products and categories use `db_modified` (PIM legacy), ContentDB pages use `Content.updated_at`, FAQ items use `modified_at` (django-utils `BaseModel`). When adding a new generator, identify the actual `auto_now=True` field on the source model — do not assume `modified_at`. When adding regression tests for product/category/contentdb generators (currently only FAQ is covered), the first assertion must validate `<lastmod>` equals the source entity's timestamp `isoformat()`. Also: any queryset that uses `.only(...)` MUST include the timestamp field, otherwise iterating triggers N+1 deferred-field reads (see `models/faq.py:FaqPage.get_active_items`).
- ContentDB import fallback tries `django_contentdb` first, then legacy `contentdb`. The active package name is exposed via `settings.CONTENTDB_PACKAGE` for runtime checks.
- URL prefix placeholders are string-substituted, not evaluated — unknown placeholders pass through unchanged and produce broken URLs. Always lint the rendered output.
- `SITEMAP_LIMIT` default is 2000 per file (README shows 10000 as an example). Google's limit is 50000; tune per project.
- `LanguageSitemap.channel_short_idx` is unique globally, not per-channel. Two channels cannot share the same short idx.
- `exclude_product_types` uses magic integer codes. The mapping lives in PIM's `ProductType` enum — keep in sync when PIM adds new product types.
- `merge_languages_in_sitemap=True` (default) produces one sitemap file per channel with hreflang alternates. `False` produces one file per (channel, language) pair — useful when languages sit on different subdomains.
- No API endpoints — this module is worker-only, triggered by management command or programmatic calls into `worker.sitemap`.
- `robots_txt` field on `LanguageSitemap` overrides the default template but sitemap entries are still appended automatically by `RobotsTxtGenerator`.
