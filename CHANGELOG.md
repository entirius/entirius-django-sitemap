# Changelog

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
