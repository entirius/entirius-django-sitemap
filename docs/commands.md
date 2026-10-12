---
title: Commands
description: The generate_sitemap management command of django-sitemap.
---

## generate_sitemap

Generates the sitemap files and `robots.txt`. Without `--domain_idx` it runs for every `DomainSitemap` entry; the
languages come from `DomainSitemap.languages`.

```bash
python manage.py generate_sitemap --domain_idx <idx>              # full pipeline (default)
python manage.py generate_sitemap --domain_idx <idx> --sitemap    # only XML files
python manage.py generate_sitemap --domain_idx <idx> --robots     # only robots.txt
python manage.py generate_sitemap                                 # every DomainSitemap entry
```

The same entry points are callable from code: `generate_sitemap(domain_sitemap)` and
`generate_robots(domain_sitemap)` in `django_sitemap.worker.sitemap`.
