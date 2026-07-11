# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import xml.etree.ElementTree as ET

from process_logger import ProcessLogger
from tqdm import tqdm

from django_sitemap import settings
from django_sitemap.worker.generators.base import BaseSitemapGenerator

try:
    from django_pim.models import ProductCategory

    STOP_CATEGORY_SITEMAP_GENERATOR = False
except ImportError:
    ProductCategory = None
    STOP_CATEGORY_SITEMAP_GENERATOR = True


class CategorySitemapGenerator(BaseSitemapGenerator):
    """
    Generator sitemap dla kategorii.
    Generuje pliki sitemap dla wszystkich aktywnych kategorii w skonfigurowanych językach.

    Zapewnia dwa tryby działania:
    1. Standardowy - osobny plik sitemap dla każdego języka (merge_languages_in_sitemap=False)
    2. Połączony - wszystkie języki w jednym pliku sitemap (merge_languages_in_sitemap=True)

    Tryb działania jest określany przez pole merge_languages_in_sitemap w modelu Channel.
    """

    def __init__(self, *args, **kwargs):
        super().__init__("categories", *args, **kwargs)
        self.set_logger(ProcessLogger("CATEGORY_SITEMAP_GENERATOR", module="django_sitemap"))
        self.merged_urlsets = {}

    def _add_log_params(self, category_idx=None, language=None):
        """
        Dodaje parametry do loggera.
        """
        if category_idx:
            self.logger.add_log_param("category_idx", category_idx)
        if language:
            self.logger.add_log_param("language", language)

    def get_all_descendants(self, category) -> list[ProductCategory]:
        descendants = []
        for subcategory in category.subcategories.all():
            descendants.append(subcategory)
            descendants.extend(self.get_all_descendants(subcategory))
        return descendants

    def get_active_categories(self, channel_idx: str) -> list[ProductCategory]:
        categories = ProductCategory.objects.filter(is_active=True, shop__idx=channel_idx)
        if settings.LIST_OF_CATEGORY_IDXES_WHICH_ARE_EXCLUDED:
            excluded_categories = self.get_excluded_categories(channel_idx)
            categories = categories.exclude(id__in=[category.id for category in excluded_categories])

        if self.sitemap_channel.skip_category_without_enabled_products:
            from django.db.models import Count, Q

            categories = categories.annotate(
                enabled_products_count=Count("products", filter=Q(products__is_enabled=True))
            ).filter(enabled_products_count__gt=0)

        return categories

    def get_excluded_categories(self, channel_idx: str) -> list[ProductCategory]:
        excluded_categories = []

        tree_category_excluded = ProductCategory.objects.filter(
            idx__in=settings.LIST_OF_CATEGORY_IDXES_WHICH_ARE_EXCLUDED, shop__idx=channel_idx
        )

        for category_excluded in tree_category_excluded:
            excluded_categories.append(category_excluded)
            excluded_categories.extend(self.get_all_descendants(category_excluded))

        return excluded_categories

    def _get_category_url(self) -> str:

        domain_with_scheme = self._get_base_url()
        path = self._replace_channel_placeholders(self.sitemap_channel.category_url)

        if path.startswith("/"):
            path = path[1:]

        if path.endswith("/"):
            path = path[:-1]

        return f"{domain_with_scheme}/{path}/"

    def add_category_to_urlset(self, urlset: ET.Element, category: ProductCategory, language: str):
        try:
            self._add_log_params(category_idx=category.idx, language=language)
            if not (category_url_key := category.url_key_t9n.get(language, None)):
                self.logger.info(f"Category {category.idx} does not have a URL key for language {language}")
                self.logger.delete_log_param("category_idx")
                self.logger.delete_log_param("language")
                return

            url = ET.SubElement(urlset, "url")
            loc = ET.SubElement(url, "loc")
            lastmod = ET.SubElement(url, "lastmod")

            formatted_url = self._get_category_url()
            formatted_url = self._get_formatted_lang_url(formatted_url, language)
            category_url = f"{formatted_url}{category_url_key}"

            loc.text = category_url
            lastmod.text = category.db_modified.isoformat()

        except Exception as e:
            self._add_log_params(category_idx=getattr(category, "idx", None), language=language)
            self.logger.exception(e)
        finally:
            self.logger.delete_log_param("category_idx")
            self.logger.delete_log_param("language")

    def process_categories_for_language(self, categories: list[ProductCategory], language: str):
        total_categories = len(categories)
        file_counter = 1
        current_categories = []

        for category in tqdm(
            categories, total=total_categories, desc=f"Processing categories for language: {language}", disable=None
        ):
            current_categories.append(category)

            if len(current_categories) >= settings.LIMIT:
                if self.sitemap_channel.merge_languages_in_sitemap:
                    merged_key = f"categories-{file_counter}"
                    if merged_key not in self.merged_urlsets:
                        self.merged_urlsets[merged_key] = self.create_base_urlset()

                    for category in current_categories:
                        self.add_category_to_urlset(self.merged_urlsets[merged_key], category, language)
                else:
                    self.dump_categories_to_file(current_categories, f"categories-{file_counter}", language)

                current_categories = []
                file_counter += 1

        if current_categories:
            if self.sitemap_channel.merge_languages_in_sitemap:
                merged_key = f"categories-{file_counter}"
                if merged_key not in self.merged_urlsets:
                    self.merged_urlsets[merged_key] = self.create_base_urlset()

                for category in current_categories:
                    self.add_category_to_urlset(self.merged_urlsets[merged_key], category, language)
            else:
                self.dump_categories_to_file(current_categories, f"categories-{file_counter}", language)

    def dump_categories_to_file(self, categories: list[ProductCategory], filepath: str, language: str):
        urlset = self.create_base_urlset()

        for category in categories:
            self.add_category_to_urlset(urlset, category, language)

        if not urlset:
            self.logger.warning(f"No categories found for {filepath}-{language}. Skipping file generation.")
            return

        self.save_xml(urlset, f"{filepath}-{language}")
        self.logger.info(f"Successfully saved sitemap file: {filepath}-{language}")

    def generate(self):
        if STOP_CATEGORY_SITEMAP_GENERATOR:
            self.logger.info("django_pim is not installed. Stopping category sitemap generator.")
            return

        categories = self.get_active_categories(self.channel_idx)
        for language in self._get_shop_languages():
            self._add_log_params(language=language)
            self.process_categories_for_language(categories, language)
            self.logger.delete_log_param("language")

        self.save_merged_files()
