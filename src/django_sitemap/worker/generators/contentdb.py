# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import xml.etree.ElementTree as ET
from typing import Any

from process_logger import ProcessLogger
from tqdm import tqdm

from django_sitemap import settings
from django_sitemap.models.contentdb import ContentDBPage
from django_sitemap.worker.generators.base import BaseSitemapGenerator

try:
    from django_sitemap.settings import CONTENTDB_PACKAGE, ContentType, Draft, Language, Published, Route

    STOP_CONTENTDB_SITEMAP_GENERATOR = False
except ImportError:
    Draft = ContentType = Language = Published = Route = CONTENTDB_PACKAGE = None
    STOP_CONTENTDB_SITEMAP_GENERATOR = True


class ContentDBSitemapGenerator(BaseSitemapGenerator):
    """
    Sitemap generator for ContentDB pages.
    Generates sitemaps for all active ContentDB pages in all configured languages.
    """

    def __init__(self, *args, **kwargs):
        super().__init__("contentdb", *args, **kwargs)
        self.is_available = hasattr(ContentDBPage, "get_active_drafts_pages")
        self.set_logger(ProcessLogger("ContentDBSitemapGenerator"))
        self.merged_urlsets = {}

    def _add_log_params(self, draft_pk=None, language=None):
        """
        Add parameters to the logger.
        """
        if draft_pk:
            self.logger.add_log_param("draft_pk", draft_pk)
        if language:
            self.logger.add_log_param("language", language)

    def get_active_drafts_pages(self, language_iso2) -> list[Any]:
        if not self.is_available:
            return []

        content_types = [slug for slug in self.sitemap_channel.contentdb_content_types_to_process.keys()]
        return ContentDBPage.get_active_drafts_pages(
            language_iso2, self.sitemap_channel.contentdb_access_rights, content_types
        )

    def _get_route_url(self, content_type: str) -> str:

        domain_with_scheme = self._get_base_url()
        all_path_by_content_type = self.sitemap_channel.contentdb_content_types_to_process
        path = None
        if content_type in self.sitemap_channel.contentdb_content_types_to_process:
            path = all_path_by_content_type.get(content_type)

            path = self._replace_channel_placeholders(path)

            if path.startswith("/"):
                path = path[1:]

            if path.endswith("/"):
                path = path[:-1]

        if path:
            return f"{domain_with_scheme}/{path}/"
        else:
            return f"{domain_with_scheme}/"

    def add_route_to_urlset(self, urlset: ET.Element, draft: Draft, language_iso2: str, currency: str | None = None):
        self._add_log_params(draft_pk=draft.pk, language=language_iso2)
        try:
            for route in draft.routes.all():
                try:
                    formatted_url = self._get_route_url(draft.content_type.slug)
                    formatted_url = self._get_formatted_lang_url(formatted_url, language_iso2)
                    formatted_url = self._get_formatted_currency_url(formatted_url, currency)
                    contentdb_url = f"{formatted_url}{route.url}"
                    lastmod_value = draft.content.updated_at.isoformat()
                    url = ET.SubElement(urlset, "url")
                    ET.SubElement(url, "loc").text = contentdb_url
                    ET.SubElement(url, "lastmod").text = lastmod_value
                except Exception as e:
                    self.logger.exception(e)
        finally:
            self.logger.delete_log_param("draft_pk")
            self.logger.delete_log_param("language")

    def dump_drafts_to_file(self, drafts: list[Draft], filepath: str, language_iso2: str, currency: str | None = None):
        urlset = self.create_base_urlset()

        for draft in drafts:
            self.add_route_to_urlset(urlset, draft, language_iso2, currency)
        if not urlset:
            self.logger.warning(f"No routes found for {filepath}-{language_iso2}. Skipping file generation.")
            return
        self.save_xml(urlset, f"{filepath}-{language_iso2.lower()}")
        self.logger.info(f"Successfully saved sitemap file: {filepath}-{language_iso2}")

    def process_drafts_batch(
        self, current_drafts: list[Draft], language_iso2: str, file_counter: int, currency: str | None = None
    ):
        suffix = self._currency_file_suffix(currency)
        if self._merge_languages():
            merged_key = f"{CONTENTDB_PACKAGE}-{file_counter}{suffix}"
            if merged_key not in self.merged_urlsets:
                self.merged_urlsets[merged_key] = self.create_base_urlset()

            for route in current_drafts:
                self.add_route_to_urlset(self.merged_urlsets[merged_key], route, language_iso2, currency)
        else:
            self.dump_drafts_to_file(
                current_drafts, f"{CONTENTDB_PACKAGE}-{file_counter}{suffix}", language_iso2, currency
            )

    def process_drafts(self, drafts_to_process: list[Draft], language_iso2: str, currency: str | None = None):
        total_drafts = len(drafts_to_process)
        file_counter = 1
        current_drafts = []

        for drafts in tqdm(drafts_to_process, total=total_drafts, desc="Processing drafts", disable=None):
            current_drafts.append(drafts)
            if len(current_drafts) >= settings.LIMIT:
                self.process_drafts_batch(current_drafts, language_iso2, file_counter, currency)

                current_drafts = []
                file_counter += 1

        if current_drafts:
            self.process_drafts_batch(current_drafts, language_iso2, file_counter, currency)

    def generate(self, **kwargs):
        if STOP_CONTENTDB_SITEMAP_GENERATOR:
            self.logger.warning("django_contentdb/contentdb is not installed. Stopping contentdb sitemap generator.")
            return

        try:
            for language_iso2 in self._get_shop_languages():
                drafts = self.get_active_drafts_pages(language_iso2)
                if not drafts:
                    self.logger.info(f"No ContentDB drafts found for {language_iso2}. Skipping.")
                    continue

                for currency in self._iter_currencies():
                    self.process_drafts(drafts, language_iso2, currency)

            msg = "ContentDB sitemap generation complete"
            self.logger.info(msg)
        except Exception as e:
            self.logger.exception(e)
            self.logger.error(f"Error generating ContentDB sitemap: {str(e)}")
        self.save_merged_files()
