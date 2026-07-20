# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import xml.etree.ElementTree as ET

from process_logger import ProcessLogger
from tqdm import tqdm

from django_sitemap import settings
from django_sitemap.models.faq import FaqPage
from django_sitemap.worker.generators.base import BaseSitemapGenerator


class FaqSitemapGenerator(BaseSitemapGenerator):
    """
    Sitemap generator for FAQ items.

    Each item produces one URL per channel language. The url_key segment is resolved
    per-language: FaqItemT9N.url_key wins when non-empty, otherwise falls back to the
    base FaqItem.url_key (which is the default-language slug).
    """

    def __init__(self, *args, **kwargs):
        super().__init__("faq", *args, **kwargs)
        self.set_logger(ProcessLogger("FAQ_SITEMAP_GENERATOR", module="django_sitemap"))
        self.merged_urlsets = {}
        self._faq_channel = None

    def _add_log_params(self, url_key=None, language=None):
        if url_key:
            self.logger.add_log_param("url_key", url_key)
        if language:
            self.logger.add_log_param("language", language)

    def _resolve_faq_channel(self):
        """Resolve FaqChannel once per generate() run."""
        if settings.FaqChannel is None:
            return None
        return settings.FaqChannel.objects.filter(idx=self.channel_idx).first()

    def _get_faq_base_url(self, language_iso2: str, currency: str | None = None) -> str:
        """URL prefix for one (language, currency). Depends only on language/currency, not on item."""
        domain_with_scheme = self._get_base_url()
        path = self._replace_channel_placeholders(self.sitemap_channel.faq_url).strip("/")
        base = f"{domain_with_scheme}/{path}/"
        base = self._get_formatted_lang_url(base, language_iso2)
        return self._get_formatted_currency_url(base, currency)

    @staticmethod
    def _resolve_url_key(item, language_iso2: str) -> str:
        """Return T9N url_key for this language when non-empty, else base item.url_key.

        Relies on item.translations being prefetched (see FaqPage.get_active_items).
        """
        target = language_iso2.lower()
        for t9n in item.translations.all():
            if t9n.language.iso2.lower() == target and t9n.url_key:
                return t9n.url_key
        return item.url_key

    def _add_item_to_urlset(self, urlset: ET.Element, item, base_url: str, language_iso2: str):
        try:
            url_key = self._resolve_url_key(item, language_iso2)
            self._add_log_params(url_key=url_key, language=language_iso2)
            url = ET.SubElement(urlset, "url")
            loc = ET.SubElement(url, "loc")
            lastmod = ET.SubElement(url, "lastmod")
            loc.text = f"{base_url}{url_key}"
            lastmod.text = item.modified_at.isoformat()
        except Exception as e:
            self.logger.exception(e)
        finally:
            self.logger.delete_log_param("url_key")
            self.logger.delete_log_param("language")

    def _dump_to_file(self, items: list, filepath: str, base_url: str, language_iso2: str):
        urlset = self.create_base_urlset()
        for item in items:
            self._add_item_to_urlset(urlset, item, base_url, language_iso2)
        self.save_xml(urlset, f"{filepath}-{language_iso2.lower()}")
        self.logger.info(f"Saved FAQ sitemap file: {filepath}-{language_iso2}")

    def _process_batch(
        self, batch: list, base_url: str, language_iso2: str, file_counter: int, currency: str | None = None
    ):
        suffix = self._currency_file_suffix(currency)
        if self._merge_languages():
            merged_key = f"{settings.FAQ_PACKAGE}-{file_counter}{suffix}"
            if merged_key not in self.merged_urlsets:
                self.merged_urlsets[merged_key] = self.create_base_urlset()
            for item in batch:
                self._add_item_to_urlset(self.merged_urlsets[merged_key], item, base_url, language_iso2)
        else:
            self._dump_to_file(batch, f"{settings.FAQ_PACKAGE}-{file_counter}{suffix}", base_url, language_iso2)

    def _process_language(self, language_iso2: str, currency: str | None = None):
        items = FaqPage.get_active_items(channel=self._faq_channel)
        if not items:
            self.logger.info(f"No active FAQ items for channel {self.channel_idx}. Skipping {language_iso2}.")
            return

        base_url = self._get_faq_base_url(language_iso2, currency)
        file_counter = 1
        current_batch = []

        # chunk_size is mandatory with prefetch_related (Django 4.1+);
        # without it prefetches are silently dropped and per-language url_key resolution breaks.
        for item in tqdm(
            items.iterator(chunk_size=settings.LIMIT),
            desc=f"Processing FAQ sitemap ({language_iso2})",
            disable=None,
        ):
            current_batch.append(item)
            if len(current_batch) >= settings.LIMIT:
                self._process_batch(current_batch, base_url, language_iso2, file_counter, currency)
                current_batch = []
                file_counter += 1

        if current_batch:
            self._process_batch(current_batch, base_url, language_iso2, file_counter, currency)

    def generate(self, **kwargs):
        if settings.FAQ_PACKAGE is None:
            self.logger.warning("django_faq is not installed. Stopping FAQ sitemap generator.")
            return

        if not self.sitemap_channel.faq_url:
            self.logger.info("faq_url not configured. Skipping FAQ sitemap generation.")
            return

        self._faq_channel = self._resolve_faq_channel()
        if self._faq_channel is None:
            self.logger.warning(f"FaqChannel idx={self.channel_idx} not found. Skipping FAQ sitemap.")
            return

        try:
            for language_iso2 in self._get_shop_languages():
                self._add_log_params(language=language_iso2)
                for currency in self._iter_currencies():
                    self._process_language(language_iso2, currency)
                self.logger.delete_log_param("language")

            self.logger.info("FAQ sitemap generation complete")
        except Exception as e:
            self.logger.exception(e)

        self.save_merged_files()
