# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import xml.etree.ElementTree as ET

from process_logger import ProcessLogger
from tqdm import tqdm

from django_sitemap import settings
from django_sitemap.signals import sitemap_product_countries
from django_sitemap.worker.generators.base import BaseSitemapGenerator
from django_sitemap.worker.pricing import get_skus_priced_in_currency

try:
    from django_pim.models import Product, ProductAttribute
    from django_pim.models.product import ProductClassEnum
    from django_pim.settings import SYSTEM_FEATURE_URL_KEY_IDX

    STOP_PRODUCT_SITEMAP_GENERATOR = False
except ImportError:
    Product = ProductAttribute = SYSTEM_FEATURE_URL_KEY_IDX = ProductClassEnum = None
    STOP_PRODUCT_SITEMAP_GENERATOR = True


class ProductSitemapGenerator(BaseSitemapGenerator):
    """
    Sitemap generator for products.
    Generates sitemaps for all active products in all configured languages.

    Three independent axes: language (LanguageSitemap.file_split_mode: WHOLE_CHANNEL merges
    languages, PER_LANGUAGE one file per language), currency (DomainSitemap.currencies - filter
    + separate files) and country (DomainSitemap.countries - separate files + placeholder;
    additional per-SKU filter via the sitemap_product_countries signal).
    """

    def __init__(self, *args, **kwargs):
        super().__init__("products", *args, **kwargs)
        self.set_logger(ProcessLogger("PRODUCT_SITEMAP_GENERATOR", module="django_sitemap"))
        self.merged_urlsets = {}
        self._currency_sku_cache = {}
        self._country_allowed_map = None

    def _add_log_params(self, sku=None, language=None):
        if sku:
            self.logger.add_log_param("sku", sku)
        if language:
            self.logger.add_log_param("language", language)

    def _get_active_products(self, currency: str | None = None, country: str | None = None) -> list[Product]:
        self._get_pim_shop()
        queryset = Product.objects.filter(
            is_enabled=True,
            shop=self.pim_shop,
            configurable_links__isnull=True,
        )

        exclude_types = self.sitemap_channel.exclude_product_types or []
        if exclude_types:
            queryset = queryset.exclude(product_class__in=exclude_types)

        if not self.sitemap_channel.custom_product_url:
            queryset = queryset.exclude(product_class=ProductClassEnum.ProductCustom)

        if currency:
            queryset = self._filter_by_currency(queryset, currency)

        if country:
            queryset = self._filter_by_country(queryset, country)

        return queryset.prefetch_related("real_product")

    def _get_country_allowed_map(self) -> dict[str, set[str]]:
        """SKU -> set of allowed ISO2 countries, from the sitemap_product_countries signal.

        Sent once per run and cached. Only SKUs the signal returns with a non-empty list get an
        entry; a SKU absent from the signal (or returned with an empty list) is assigned to NO
        country and is dropped from every country file (fail-closed). No receiver ⇒ empty map ⇒
        no product is served in any country.
        """
        if self._country_allowed_map is None:
            allowed: dict[str, set[str]] = {}
            responses = sitemap_product_countries.send(sender=self.__class__, channel_idx=self.channel_idx)
            for _receiver, result in responses:
                if not result:
                    continue
                for sku, countries in result.items():
                    if countries:
                        allowed.setdefault(sku, set()).update(c.upper() for c in countries)
            self._country_allowed_map = allowed
        return self._country_allowed_map

    def _filter_by_country(self, queryset, country: str):
        """Keep only products the signal explicitly assigns to `country` (whitelist / fail-closed).

        A product is served in a country only when the signal returned that country for its SKU.
        Products absent from the signal (or with an empty list) are assigned to no country and are
        dropped everywhere; the resulting empty country files are skipped when saving.
        """
        allowed_map = self._get_country_allowed_map()
        country = country.upper()
        allowed_skus = [sku for sku, countries in allowed_map.items() if country in countries]
        return queryset.filter(real_product__sku__in=allowed_skus)

    def _filter_by_currency(self, queryset, currency: str):
        """Restrict to products priced in `currency` for this channel (via django-pricemanager).

        The per-currency SKU set is cached so it is fetched once per currency, not once per
        (language, currency) pair.
        """
        if currency not in self._currency_sku_cache:
            self._currency_sku_cache[currency] = get_skus_priced_in_currency(self.channel_idx, currency)

        skus = self._currency_sku_cache[currency]
        if skus is None:
            self.logger.warning(
                f"Currency {currency} configured but django-pricemanager is unavailable; skipping currency filter."
            )
            return queryset
        return queryset.filter(real_product__sku__in=skus)

    def _get_product_url(self) -> str:
        domain_with_scheme = self._get_base_url()
        path = self._replace_channel_placeholders(self.sitemap_channel.product_url)

        if path.startswith("/"):
            path = path[1:]

        if path.endswith("/"):
            path = path[:-1]

        return f"{domain_with_scheme}/{path}/"

    def _get_custom_product_url(self) -> str:
        domain_with_scheme = self._get_base_url()
        path = self._replace_channel_placeholders(self.sitemap_channel.custom_product_url)

        if path.startswith("/"):
            path = path[1:]

        if path.endswith("/"):
            path = path[:-1]

        return f"{domain_with_scheme}/{path}/"

    def _get_product_url_key(self, product, language, url_keys_dict=None):
        if url_keys_dict and product.pk in url_keys_dict:
            return url_keys_dict[product.pk].get(language, None)

        pa_url_key = ProductAttribute.objects.filter(
            product__pk=product.pk, feature__idx=SYSTEM_FEATURE_URL_KEY_IDX
        ).first()
        if pa_url_key:
            return pa_url_key.value_txt_t9n.get(language, None)
        return None

    def _add_product_to_urlset(
        self,
        urlset: ET.Element,
        product: Product,
        language: str,
        currency: str | None = None,
        country: str | None = None,
        url_keys_dict=None,
    ):
        try:
            pa_url_key = self._get_product_url_key(product, language, url_keys_dict)
            if not pa_url_key:
                return
            url = ET.SubElement(urlset, "url")
            loc = ET.SubElement(url, "loc")
            lastmod = ET.SubElement(url, "lastmod")

            if product.product_class == ProductClassEnum.ProductCustom:
                formatted_url = self._get_custom_product_url()
            else:
                formatted_url = self._get_product_url()
            formatted_url = self._get_formatted_lang_url(formatted_url, language)
            formatted_url = self._get_formatted_currency_url(formatted_url, currency)
            formatted_url = self._get_formatted_country_url(formatted_url, country)
            product_url = f"{formatted_url}{pa_url_key}"

            loc.text = product_url
            lastmod.text = product.db_modified.isoformat()

        except Exception as e:
            sku = getattr(product, "sku", None)
            if not sku and hasattr(product, "real_product"):
                sku = getattr(product.real_product, "sku", None)
            self._add_log_params(sku=sku, language=language)
            self.logger.exception(e)
        finally:
            self.logger.delete_log_param("sku")
            self.logger.delete_log_param("language")

    def process_products_for_language(self, language: str, currency: str | None = None, country: str | None = None):
        file_counter = 1
        suffix = f"{self._currency_file_suffix(currency)}{self._country_file_suffix(country)}"
        products_query = self._get_active_products(currency, country)

        current_batch = []
        product_ids = []

        for i, product in enumerate(
            tqdm(
                products_query.iterator(chunk_size=settings.LIMIT),
                desc=f"Processing products sitemap ({language})",
                disable=None,
            )
        ):
            current_batch.append(product)
            product_ids.append(product.pk)

            if len(current_batch) >= settings.LIMIT:
                url_keys_dict = self._prefetch_url_keys(product_ids)

                if self._merge_languages():
                    merged_key = f"products-{file_counter}{suffix}"
                    if merged_key not in self.merged_urlsets:
                        self.merged_urlsets[merged_key] = self.create_base_urlset()

                    for product in current_batch:
                        self._add_product_to_urlset(
                            self.merged_urlsets[merged_key], product, language, currency, country, url_keys_dict
                        )
                else:
                    self.dump_products_to_file(
                        current_batch, f"products-{file_counter}{suffix}", language, currency, country, url_keys_dict
                    )

                file_counter += 1
                current_batch = []
                product_ids = []

        if current_batch:
            url_keys_dict = self._prefetch_url_keys(product_ids)

            if self._merge_languages():
                merged_key = f"products-{file_counter}{suffix}"
                if merged_key not in self.merged_urlsets:
                    self.merged_urlsets[merged_key] = self.create_base_urlset()

                for product in current_batch:
                    self._add_product_to_urlset(
                        self.merged_urlsets[merged_key], product, language, currency, country, url_keys_dict
                    )
            else:
                self.dump_products_to_file(
                    current_batch, f"products-{file_counter}{suffix}", language, currency, country, url_keys_dict
                )

    def _prefetch_url_keys(self, product_ids):
        """Fetch all URL keys for the list of products and return them as a dictionary."""
        url_keys_dict = {}

        url_keys = ProductAttribute.objects.filter(product__pk__in=product_ids, feature__idx=SYSTEM_FEATURE_URL_KEY_IDX)

        for url_key in url_keys:
            url_keys_dict[url_key.product_id] = url_key.value_txt_t9n

        return url_keys_dict

    def dump_products_to_file(
        self,
        products: list[Product],
        filepath: str,
        language: str,
        currency: str | None = None,
        country: str | None = None,
        url_keys_dict=None,
    ):
        urlset = self.create_base_urlset()
        for product in products:
            self._add_product_to_urlset(urlset, product, language, currency, country, url_keys_dict)

        if not urlset:
            self.logger.warning(f"No products found for {filepath}-{language}. Skipping file generation.")
            return

        self.save_xml(urlset, f"{filepath}-{language}")

    def save_merged_files(self):
        """Save merged sitemap files (when the split mode merges languages)."""
        if not self._merge_languages():
            return

        self._add_log_params(language="merged")
        if not self.merged_urlsets:
            self.logger.warning(f"No merged sitemap files to save for domain {self.domain_sitemap.idx}")
            return

        self.logger.info(f"Saving {len(self.merged_urlsets)} merged sitemap files for domain {self.domain_sitemap.idx}")

        for key, urlset in self.merged_urlsets.items():
            if len(urlset) == 0:
                continue
            try:
                self.save_xml(urlset, key)
                self.logger.info(f"Successfully saved merged sitemap file: {key}")
            except Exception as e:
                self.logger.add_log_param_once("key", key)
                self.logger.exception(e)
        self.logger.delete_log_param("language")
        self.merged_urlsets = {}

    def generate(self):
        if STOP_PRODUCT_SITEMAP_GENERATOR:
            self.logger.warning("django_pim is not installed. Stopping product sitemap generator.")
            return
        languages = self._get_shop_languages()
        for language in languages:
            self._add_log_params(language=language)
            for currency in self._iter_currencies():
                for country in self._iter_countries():
                    self.process_products_for_language(language, currency, country)
            self.logger.delete_log_param("language")

        self.save_merged_files()
