# entirius-django-sitemap

A Django module that generates multilingual XML sitemaps and `robots.txt` files for storefronts of Entirius, the
open-source modular ecommerce platform. It writes one sitemap per content type (products, categories, custom
products, content pages, FAQ items), a sitemap index and a `robots.txt` for every channel domain.

[![PyPI](https://img.shields.io/pypi/v/entirius-django-sitemap.svg)](https://pypi.org/project/entirius-django-sitemap/)
[![Python](https://img.shields.io/pypi/pyversions/entirius-django-sitemap.svg)](https://pypi.org/project/entirius-django-sitemap/)
[![License: MPL-2.0](https://img.shields.io/badge/license-MPL--2.0-blue.svg)](https://github.com/entirius/entirius-django-sitemap/blob/develop/LICENSE)

## What it does

- Generates sitemap files per content type and a sitemap index for each channel domain.
- Builds a `robots.txt` per domain that references the generated sitemaps.
- Writes one URL per item and language, merged into one file per channel or split per language.
- Builds URLs from prefix templates with language and channel placeholders.
- Skips a content type when its source module (products, content, FAQ) is not installed.

## Installation

```shell
uv add entirius-django-sitemap
pip install entirius-django-sitemap
```

```python
INSTALLED_APPS = [
    ...
    "django_regional",
    "django_sitemap",
]
```

The module has no HTTP endpoints, so there is no URL include. No setting is required; optional settings
(`SITEMAP_URL_HOST`, `SITEMAP_FORMAT_XML`, `SITEMAP_LIMIT`, `SITEMAP_ROOT_DIR`, `SITEMAP_ROBOTS_TEMPLATE_PATH`,
`LIST_OF_CATEGORY_IDXES_WHICH_ARE_EXCLUDED`) are described in
https://github.com/entirius/entirius-django-sitemap/blob/develop/AGENTS.md (section Settings).

Each content source is an extra — `pim` (products and categories), `contentdb` (content pages), `faq` (FAQ items):

```shell
uv add "entirius-django-sitemap[pim,contentdb,faq]"
```

## Quick start

```python
from django_sitemap.models import DomainSitemap
from django_sitemap.worker.sitemap import generate_robots, generate_sitemap

domain = DomainSitemap.objects.get(idx="shop-en")
generate_sitemap(domain)
generate_robots(domain)
```

The same from the command line, for one domain or for all of them:

```shell
python manage.py generate_sitemap --domain_idx shop-en
python manage.py generate_sitemap
```

## Requirements

- Python 3.11 or newer, Django 4.0 or newer.
- Entirius packages pulled in: `entirius-django-regional`, `entirius-py-process-logger`.
- Optional, through the extras: `entirius-django-pim`, `entirius-django-contentdb`, `entirius-django-faq`.

## Documentation

- Module docs: https://github.com/entirius/entirius-django-sitemap/tree/develop/docs
- Entirius documentation: https://docs.entirius.com/
- Changelog: https://github.com/entirius/entirius-django-sitemap/blob/develop/CHANGELOG.md

## Part of Entirius

This module runs inside the Entirius backend service (Volkanos) and reads from the product, content and FAQ modules.

- Backend service: https://github.com/entirius/entirius-service-volkanos
- Docker harness: https://github.com/entirius/entirius-zeno
- Sibling modules: https://github.com/entirius/entirius-django-pim, https://github.com/entirius/entirius-django-contentdb,
  https://github.com/entirius/entirius-django-faq

## Development

```shell
make install     # sync dependencies (uv)
make check       # lint + format check (ruff)
make test        # test suite (pytest + pytest-django, needs PostgreSQL via DATABASE_URL)
```

Development and agent instructions: https://github.com/entirius/entirius-django-sitemap/blob/develop/AGENTS.md

## License

Mozilla Public License 2.0 (MPL-2.0) — see https://github.com/entirius/entirius-django-sitemap/blob/develop/LICENSE.
