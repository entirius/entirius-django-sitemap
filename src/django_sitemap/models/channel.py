# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models


class LanguageSitemap(models.Model):
    idx = models.CharField(max_length=255, unique=True, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    channel_short_idx = models.CharField(max_length=255, unique=True, null=True, blank=True)
    product_url = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="URL prefix for product pages. Use {{language_iso2}} as a placeholder for language iso2. Also use {{channel_short_idx}} as a placeholder for channel short idx. Supports modifiers: {{language_iso2.lower()}}, {{language_iso2.upper()}}.",
    )
    category_url = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="URL prefix for category pages. Use {{language_iso2}} as a placeholder for language iso2. Also use {{channel_short_idx}} as a placeholder for channel short idx. Supports modifiers: {{language_iso2.lower()}}, {{language_iso2.upper()}}.",
    )
    custom_product_url = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="URL prefix for custom product pages. If empty, custom products will not be included in sitemap. Use {{language_iso2}} as a placeholder for language iso2. Also use {{channel_short_idx}} as a placeholder for channel short idx. Supports modifiers: {{language_iso2.lower()}}, {{language_iso2.upper()}}.",
    )
    faq_url = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="URL prefix for FAQ item pages. If empty, FAQ items will not be included in sitemap. Use {{language_iso2}} as a placeholder for language iso2. Also use {{channel_short_idx}} as a placeholder for channel short idx. Supports modifiers: {{language_iso2.lower()}}, {{language_iso2.upper()}}. Example: '{{language_iso2.lower()}}/faq'",
    )
    contentdb_content_types_to_process = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        help_text="Content types to process. Use {{language_iso2}} as a placeholder for language iso2. Also use {{channel_short_idx}} as a placeholder for channel short idx. Supports modifiers: {{language_iso2.lower()}}, {{language_iso2.upper()}}. Example: {'blog-post': '{{language_iso2.lower()}}/porady', 'static-page': '{{channel_short_idx}}/static'}",
    )
    contentdb_access_rights = models.JSONField(
        blank=True,
        null=True,
        default=list,
        help_text="Access rights contentdb. Example: [1,2]",
    )
    merge_languages_in_sitemap = models.BooleanField(
        default=True,
        help_text="Jeśli zaznaczone, pliki sitemap dla różnych języków będą łączone w jeden plik dla danego kanału.",
    )
    skip_category_without_enabled_products = models.BooleanField(
        default=True,
        help_text="Jeśli zaznaczone, kategorie bez włączonych produktów nie będą generowane w sitemap.",
    )
    exclude_product_types = models.JSONField(
        blank=True,
        null=True,
        default=list,
        help_text="Product types to exclude from sitemap. Values: 0=ProductBase, 1=ProductSimple, 2=ProductConfigurable, 3=ProductBundle, 4=ProductCustom. Example: [2, 3] excludes Configurable and Bundle products.",
    )
    robots_txt = models.TextField(
        blank=True,
        null=True,
        help_text="Custom robots.txt content for this channel. If empty, the default template will be used. Sitemap entries are appended automatically.",
    )

    def __str__(self):
        return self.idx if self.idx else "All channels"

    def save(self, *args, **kwargs):

        if self.product_url:
            if self.product_url.endswith("/"):
                self.product_url = self.product_url[:-1]
            if self.product_url.startswith("/"):
                self.product_url = self.product_url[1:]

        if self.category_url:
            if self.category_url.endswith("/"):
                self.category_url = self.category_url[:-1]
            if self.category_url.startswith("/"):
                self.category_url = self.category_url[1:]

        if self.custom_product_url:
            if self.custom_product_url.endswith("/"):
                self.custom_product_url = self.custom_product_url[:-1]
            if self.custom_product_url.startswith("/"):
                self.custom_product_url = self.custom_product_url[1:]

        if self.faq_url:
            if self.faq_url.endswith("/"):
                self.faq_url = self.faq_url[:-1]
            if self.faq_url.startswith("/"):
                self.faq_url = self.faq_url[1:]

        super().save(*args, **kwargs)
