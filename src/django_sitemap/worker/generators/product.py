# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import xml.etree.ElementTree as ET

from process_logger import ProcessLogger
from tqdm import tqdm

from django_sitemap import settings
from django_sitemap.worker.generators.base import BaseSitemapGenerator

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

    Zapewnia dwa tryby działania:
    1. Standardowy - osobny plik sitemap dla każdego języka (merge_languages_in_sitemap=False)
    2. Połączony - wszystkie języki w jednym pliku sitemap (merge_languages_in_sitemap=True)

    Tryb działania jest określany przez pole merge_languages_in_sitemap w modelu Channel.
    """

    def __init__(self, *args, **kwargs):
        super().__init__("products", *args, **kwargs)
        self.set_logger(ProcessLogger("PRODUCT_SITEMAP_GENERATOR", module="django_sitemap"))
        self.merged_urlsets = {}

    def _add_log_params(self, sku=None, language=None):
        if sku:
            self.logger.add_log_param("sku", sku)
        if language:
            self.logger.add_log_param("language", language)

    def _get_active_products(self) -> list[Product]:
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

        return queryset.prefetch_related("real_product")

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

    def _add_product_to_urlset(self, urlset: ET.Element, product: Product, language: str, url_keys_dict=None):
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

    def process_products_for_language(self, language: str):
        file_counter = 1
        products_query = self._get_active_products()

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

                if self.sitemap_channel.merge_languages_in_sitemap:
                    merged_key = f"products-{file_counter}"
                    if merged_key not in self.merged_urlsets:
                        self.merged_urlsets[merged_key] = self.create_base_urlset()

                    for product in current_batch:
                        self._add_product_to_urlset(self.merged_urlsets[merged_key], product, language, url_keys_dict)
                else:
                    self.dump_products_to_file(current_batch, f"products-{file_counter}", language, url_keys_dict)

                file_counter += 1
                current_batch = []
                product_ids = []

        if current_batch:
            url_keys_dict = self._prefetch_url_keys(product_ids)

            if self.sitemap_channel.merge_languages_in_sitemap:
                merged_key = f"products-{file_counter}"
                if merged_key not in self.merged_urlsets:
                    self.merged_urlsets[merged_key] = self.create_base_urlset()

                for product in current_batch:
                    self._add_product_to_urlset(self.merged_urlsets[merged_key], product, language, url_keys_dict)
            else:
                self.dump_products_to_file(current_batch, f"products-{file_counter}", language, url_keys_dict)

    def _prefetch_url_keys(self, product_ids):
        """Pobiera wszystkie klucze URL dla listy produktów i zwraca je jako słownik."""
        url_keys_dict = {}

        url_keys = ProductAttribute.objects.filter(product__pk__in=product_ids, feature__idx=SYSTEM_FEATURE_URL_KEY_IDX)

        for url_key in url_keys:
            url_keys_dict[url_key.product_id] = url_key.value_txt_t9n

        return url_keys_dict

    def dump_products_to_file(self, products: list[Product], filepath: str, language: str, url_keys_dict=None):
        urlset = self.create_base_urlset()
        for product in products:
            self._add_product_to_urlset(urlset, product, language, url_keys_dict)

        if not urlset:
            self.logger.warning(f"No products found for {filepath}-{language}. Skipping file generation.")
            return

        self.save_xml(urlset, f"{filepath}-{language}")

    def save_merged_files(self):
        """Zapisuje połączone pliki sitemap (gdy merge_languages_in_sitemap=True)."""
        if not self.sitemap_channel.merge_languages_in_sitemap:
            return

        self._add_log_params(language="merged")
        if not self.merged_urlsets:
            self.logger.warning(f"No merged sitemap files to save for domain {self.domain_sitemap.idx}")
            return

        self.logger.info(f"Saving {len(self.merged_urlsets)} merged sitemap files for domain {self.domain_sitemap.idx}")

        for key, urlset in self.merged_urlsets.items():
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
            self.process_products_for_language(language)
            self.logger.delete_log_param("language")

        self.save_merged_files()
