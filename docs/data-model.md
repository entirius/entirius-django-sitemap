---
title: Data Model
description: Entities of django-sitemap, URL prefix placeholders and product type exclusions.
---

| Entity | Key Fields | Relationships |
|---|---|---|
| Channel | idx (unique) | Referenced by DomainSitemap |
| DomainSitemap | idx (unique), domain_url | FK → Channel, FK → LanguageSitemap, M2M → `django_regional.Language` |
| LanguageSitemap | idx, channel_short_idx (both unique), is_active, product_url, category_url, custom_product_url, faq_url, contentdb_content_types_to_process (JSON), contentdb_access_rights (JSON), file_split_mode, skip_category_without_enabled_products, exclude_product_types (JSON), robots_txt (custom override) | Back-reference from DomainSitemap |

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
