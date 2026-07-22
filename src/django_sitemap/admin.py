# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django import forms
from django.contrib import admin

from django_sitemap.models import Channel, DomainSitemap, LanguageSitemap

PRODUCT_TYPE_CHOICES = [
    (0, "ProductBase"),
    (1, "ProductSimple"),
    (2, "ProductConfigurable"),
    (3, "ProductBundle"),
    (4, "ProductCustom"),
]


class LanguageSitemapAdminForm(forms.ModelForm):
    exclude_product_types = forms.MultipleChoiceField(
        choices=PRODUCT_TYPE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Select product types to exclude from the sitemap.",
    )

    class Meta:
        model = LanguageSitemap
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.exclude_product_types:
            self.fields["exclude_product_types"].initial = [str(x) for x in self.instance.exclude_product_types]

    def clean_exclude_product_types(self):
        data = self.cleaned_data.get("exclude_product_types", [])
        return [int(x) for x in data] if data else []


@admin.register(LanguageSitemap)
class LanguageSitemapAdmin(admin.ModelAdmin):
    form = LanguageSitemapAdminForm
    list_display = [
        "idx",
        "is_active",
        "channel_short_idx",
        "product_url",
        "custom_product_url",
        "category_url",
        "file_split_mode",
    ]
    search_fields = ["idx", "channel_short_idx"]
    list_filter = ["is_active", "file_split_mode"]
    list_editable = [
        "is_active",
        "product_url",
        "custom_product_url",
        "category_url",
        "file_split_mode",
    ]


class DomainSitemapInline(admin.TabularInline):
    model = DomainSitemap
    extra = 0
    fields = ["idx", "domain_url", "language_sitemap", "config_split_mode", "languages", "currencies", "countries"]
    readonly_fields = ["config_split_mode"]
    filter_horizontal = ["languages", "currencies", "countries"]
    show_change_link = True

    @admin.display(description="File split mode (from config)")
    def config_split_mode(self, obj):
        """Read-only echo of the linked LanguageSitemap.file_split_mode so the setting is visible here.
        The setting itself is edited on the LanguageSitemap (config) page."""
        if obj and obj.language_sitemap_id:
            return obj.language_sitemap.get_file_split_mode_display()
        return "—"


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ["idx", "domain_count"]
    search_fields = ["idx"]
    inlines = [DomainSitemapInline]

    @admin.display(description="Domains")
    def domain_count(self, obj):
        return obj.domain_sitemaps.count()


@admin.register(DomainSitemap)
class DomainSitemapAdmin(admin.ModelAdmin):
    list_display = [
        "idx",
        "channel",
        "domain_url",
        "language_sitemap",
        "languages_list",
        "currencies_list",
        "countries_list",
    ]
    search_fields = ["idx", "domain_url"]
    list_filter = ["channel", "language_sitemap"]
    filter_horizontal = ["languages", "currencies", "countries"]

    @admin.display(description="Languages")
    def languages_list(self, obj):
        return ", ".join(obj.languages.values_list("iso2", flat=True))

    @admin.display(description="Currencies")
    def currencies_list(self, obj):
        return ", ".join(obj.currencies.values_list("iso3", flat=True)) or "all"

    @admin.display(description="Countries")
    def countries_list(self, obj):
        return ", ".join(obj.countries.values_list("iso2", flat=True)) or "all"
