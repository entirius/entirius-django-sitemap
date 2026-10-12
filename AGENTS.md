# AGENTS.md

`entirius-django-sitemap` (Django app `django_sitemap`) — multilingual XML sitemap and robots.txt generator of
Entirius. Produces separate sitemaps per content type (products, categories, custom products, ContentDB pages, FAQ
items), a sitemap index, and a `robots.txt` per channel-domain. Supports language-scoped URL prefixes and
optional language merging into a single file.

## Commands

| Command | Meaning |
|---|---|
| `make install` | sync dependencies (uv, incl. extras) |
| `make check` | lint + format-check (ruff) |
| `make fix` | auto-fix lint + format |
| `make test` | test suite (pytest + pytest-django) |

Tests need PostgreSQL: set `DATABASE_URL` (the default in `tests/settings.py` points at a local postgres).

## Conventions

- English only: code, docs, commits, branches, PRs.
- MPL-2.0: every non-trivial source file carries the license header (pre-commit inserts it).
- Toolchain: uv + ruff + hatchling + pytest; all config in `pyproject.toml`; `uv.lock` committed.
- Git flow: `master` (production) + `develop` (integration); changes land via PR; semver tag on `master`.
- Never rename the package / Django app_label / DB table prefix `django_sitemap` — it is a schema contract.
- Migrations are part of the public contract — never edit an already released migration.
- Default: do not commit — git is the user's call.
- No AI attribution in commits or PR descriptions.

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
│   └── generate_sitemap.py          # python manage.py generate_sitemap [--domain_idx <idx>] [--sitemap] [--robots]
│
├── templates/admin/                 # sitemap.xml, robots.txt Django templates
└── migrations/
```

Generation flow: `generate_sitemap` management command iterates `DomainSitemap` rows (one when `--domain_idx` is given, else all), instantiates a `SitemapCoordinator` per domain, which runs each generator (product, custom products included → category → ContentDB → FAQ → index); `robots.txt` is written separately by `generate_robots`.

Soft dependencies are detected at import in `settings.py` / generators: `django_contentdb` (or legacy `contentdb`),
`django_faq`, `django_pim`. A missing one skips its generator; details in `docs/index.md` § Soft Dependencies.

| Topic | Where |
|---|---|
| Overview, soft dependencies, URL prefix placeholders | `docs/index.md` |
| Data model | `docs/data-model.md` |
| Management command | `docs/commands.md` |
| Testing | `docs/testing.md` |

## Settings

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

The robots.txt template path is `SITEMAP_ROBOTS_TEMPLATE_PATH` (default: the bundled `templates/admin/robots.txt`).

## Gotchas

- `<lastmod>` source field differs per generator because upstream models do not share a base: products and categories use `db_modified` (PIM legacy), ContentDB pages use `Content.updated_at`, FAQ items use `modified_at` (django-utils `BaseModel`). When adding a new generator, identify the actual `auto_now=True` field on the source model — do not assume `modified_at`. When adding regression tests for product/category/contentdb generators (currently only FAQ is covered), the first assertion must validate `<lastmod>` equals the source entity's timestamp `isoformat()`. Also: any queryset that uses `.only(...)` MUST include the timestamp field, otherwise iterating triggers N+1 deferred-field reads (see `models/faq.py:FaqPage.get_active_items`).
- ContentDB import fallback tries `django_contentdb` first, then legacy `contentdb`. The active package name is exposed via `settings.CONTENTDB_PACKAGE` for runtime checks.
- URL prefix placeholders are string-substituted, not evaluated — unknown placeholders pass through unchanged and produce broken URLs. Always lint the rendered output.
- `SITEMAP_LIMIT` default is 2000 per file. Google's limit is 50000; tune per project.
- `LanguageSitemap.channel_short_idx` is unique globally, not per-channel. Two channels cannot share the same short idx.
- `exclude_product_types` uses magic integer codes. The mapping lives in PIM's `ProductClassEnum` — keep in sync when PIM adds new product types.
- `file_split_mode=WHOLE_CHANNEL` (default) produces one sitemap file per channel with all languages inside. `PER_LANGUAGE` produces one file per (channel, language) pair — useful when languages sit on different subdomains.
- No API endpoints — this module is worker-only, triggered by management command or programmatic calls into `worker.sitemap`.
- `robots_txt` field on `LanguageSitemap` overrides the default template but sitemap entries are still appended automatically by `RobotsTxtGenerator`.
