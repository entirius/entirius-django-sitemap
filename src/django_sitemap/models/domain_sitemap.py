# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models

from .channel import LanguageSitemap


class Channel(models.Model):
    idx = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.idx


class DomainSitemap(models.Model):
    idx = models.CharField(max_length=255, unique=True)
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name="domain_sitemaps")
    domain_url = models.CharField(max_length=2056)
    languages = models.ManyToManyField("django_regional.Language")
    countries = models.ManyToManyField(
        "django_regional.Country",
        blank=True,
        help_text=(
            "Countries this domain serves (main pool). Empty means no country dimension. When set, "
            "one file set per country + {{country_iso2}} placeholders. A connected "
            "`sitemap_product_countries` signal receiver can additionally narrow individual SKUs to a "
            "subset of these countries; a SKU absent from the signal (or with an empty list) is served "
            "in all of them."
        ),
    )
    currencies = models.ManyToManyField(
        "django_regional.Currency",
        blank=True,
        help_text=(
            "Currencies this domain serves. Empty means all currencies (no currency filtering). "
            "When set, products are restricted to those priced in the currency and {{currency_iso3}} "
            "placeholders are rendered per currency."
        ),
    )
    language_sitemap = models.ForeignKey(LanguageSitemap, on_delete=models.CASCADE, related_name="domain_sitemaps")

    def __str__(self):
        return f"{self.idx} ({self.domain_url})"
