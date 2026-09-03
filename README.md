# django-sitemap

Multilingual XML sitemap and robots.txt generator for Volkanos PWAs — separate sitemaps per
content type (products, categories, custom products, ContentDB pages, FAQ items), a sitemap
index and a `robots.txt` per channel-domain. Supports language-scoped URL prefixes, alternate
language links (hreflang) and optional language merging into a single file.

## Installation

```shell
pip install entirius-django-sitemap
```

Add the app to your project:

```python
INSTALLED_APPS = [
    ...
    "django_sitemap",
]
```

Soft integrations — install the matching extra to enable a generator (each degrades gracefully
when absent):

```shell
pip install "entirius-django-sitemap[pim,contentdb,faq]"
```

## Usage

```shell
python manage.py generate_sitemap {shop_idx}
python manage.py generate_sitemap {shop_idx} --languages en de fr
```

Configuration (service settings):

```python
SITEMAP_URL_HOST = "https://shop.example.com"
SITEMAP_FORMAT_XML = True
SITEMAP_LIMIT = 2000            # max URLs per sitemap file
SITEMAP_ROOT_DIR = MEDIA_ROOT   # output root

# Optional: custom robots.txt template, defaults to the one shipped with the app
SITEMAP_ROBOTS_TEMPLATE_PATH = "/etc/sitemap/robots.txt"
```

The robots.txt template holds directives only (`User-agent`, `Allow`, `Disallow`) — `Sitemap:`
lines are appended during generation. A non-empty `LanguageSitemap.robots_txt` takes precedence
over the template file.

## Development

```shell
make install     # sync dependencies (uv)
make check       # lint + format check (ruff)
make test        # test suite (pytest + pytest-django, postgres via DATABASE_URL)
```

Architecture and model reference: [AGENTS.md](AGENTS.md).

## License

Mozilla Public License 2.0 — see [LICENSE](LICENSE).
