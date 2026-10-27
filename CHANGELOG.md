# Changelog

## 4.0.2rc1 — 2026-10-26

- Docs: `SITEMAP_ROBOTS_TEMPLATE_PATH` (default: the bundled `templates/admin/robots.txt`) is documented. The file
  is copied verbatim, not rendered, and holds directives only; `Sitemap:` lines are appended during generation, and a
  non-empty `LanguageSitemap.robots_txt` takes precedence. `docs/index.md` names `file_split_mode` in place of
  `merge_languages_in_sitemap` (renamed in 4.0.1). Behaviour unchanged.
- Dev lock refreshed (open Dependabot alerts): Django 5.2.18 / 6.0.9, djangorestframework 3.18.3, PyJWT 2.15.1,
  sqlparse 0.6.0, urllib3 2.8.0. The package's dependency ranges are unchanged.

## 4.0.1 — 2026-07-22

- File split mode and per-domain countries/currencies.
- `robots.txt` fix.

## 4.0.0 — 2026-07-11

- Initial public release: channel-scoped XML sitemap generation for PIM
  products and categories, ContentDB pages, and FAQ items — per-language
  files plus `robots.txt` assembly.
- `<lastmod>` reflects the real entity modification time (ISO 8601 with
  timezone), not the generation time.
- Soft imports of source modules — generators no-op when a module is not
  installed.
- Migrations squashed into a single initial migration for the Entirius epoch.
