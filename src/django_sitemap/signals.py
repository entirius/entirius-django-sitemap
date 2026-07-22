# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.dispatch import Signal

# Sent once per generation run (by the product sitemap generator) to collect per-SKU country
# availability, used as an ADDITIONAL filter on top of DomainSitemap.countries.
#
# kwargs sent:
#   channel_idx: str        -- the channel being generated
#
# Each receiver returns: dict[str, list[str]]  ->  {"<sku>": ["US", "GB", ...], ...}
# (country codes are ISO 3166-1 alpha-2, matched case-insensitively against DomainSitemap.countries).
#
# Semantics of the merged response (union of countries per SKU across receivers):
#   - non-empty list for a SKU  -> that SKU is served ONLY in those countries (∩ the M2M pool)
#   - empty list, or SKU absent -> that SKU is served in ALL of the domain's countries
#   - no receiver connected     -> no country filtering at all
sitemap_product_countries = Signal()
