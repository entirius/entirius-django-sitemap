---
title: Testing
description: How to run the django-sitemap test suite and what it covers.
---

Tests run on postgres via `DATABASE_URL` (CI provides a postgres service; locally point it at any
postgres 15+).

```bash
make install
make test
```

Test suite covers `LanguageSitemap.faq_url` normalization, `FaqPage.get_active_items` channel scoping, and `FaqSitemapGenerator` end-to-end (guard paths, URL formatting, merged/per-language XML output).
