# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod

from process_logger import ProcessLoggerMixin
from tqdm import tqdm

from django_sitemap import settings
from django_sitemap.models import DomainSitemap, LanguageSitemap


class BaseSitemapGenerator(ProcessLoggerMixin, ABC):
    name = None
    channel_idx = None
    _module_name = None
    pim_shop = None
    sitemap_channel: LanguageSitemap = None
    domain_sitemap: DomainSitemap = None

    def __init__(self, name: str, domain_sitemap: DomainSitemap):
        self.name = name
        self.domain_sitemap = domain_sitemap
        self.channel_idx = domain_sitemap.channel.idx
        self._module_name = self.__class__.__module__
        self.sitemap_channel = domain_sitemap.language_sitemap
        self.pim_shop = self._get_pim_shop()
        self.merged_urlsets = {}

    def ensure_sitemap_directory(self):
        if not os.path.exists(settings.SITEMAP_PATH):
            os.makedirs(settings.SITEMAP_PATH)

    def _get_pim_shop(self):
        if not self.pim_shop:
            try:
                from django_pim.models import Shop
            except ImportError:
                return None
            try:
                self.pim_shop = Shop.objects.get(idx=self.channel_idx)
            except Shop.DoesNotExist:
                self.logger.error(f"Shop with idx {self.channel_idx} does not exist.")
                raise
        return self.pim_shop

    def _get_shop_languages(self) -> list[str]:
        domain_languages = set(self.domain_sitemap.languages.values_list("iso2", flat=True))
        if self.pim_shop:
            shop_languages = set(self.pim_shop.languages.values_list("iso2", flat=True))
            return list(domain_languages & shop_languages)
        return list(domain_languages)

    @staticmethod
    def _get_formatted_lang_url(url: str, language: str):
        """
        Replace language placeholders with actual language code.
        Supports:
        - {{language_iso2}} - original case
        - {{language_iso2.lower()}} - lowercase
        - {{language_iso2.upper()}} - uppercase
        """
        url = url.replace("{{language_iso2.lower()}}", language.lower())
        url = url.replace("{{language_iso2.upper()}}", language.upper())
        url = url.replace("{{language_iso2}}", language)
        return url

    def _replace_channel_placeholders(self, url: str) -> str:
        """Replace {{channel_short_idx}} placeholder, safe when channel_short_idx is None."""
        return url.replace("{{channel_short_idx}}", self.sitemap_channel.channel_short_idx or "")

    def _get_base_url(self) -> str:
        domain_with_scheme = self.domain_sitemap.domain_url

        if not domain_with_scheme.startswith("http"):
            domain_with_scheme = "https://" + domain_with_scheme

        if domain_with_scheme.endswith("/"):
            domain_with_scheme = domain_with_scheme[:-1]

        return domain_with_scheme

    def save_xml(self, data: ET.Element, filename: str):
        if not os.path.exists(settings.TEMPORARY_PATH):
            os.makedirs(settings.TEMPORARY_PATH)
        channel_dir = os.path.join(settings.TEMPORARY_PATH, self.domain_sitemap.idx)
        if not os.path.exists(channel_dir):
            os.makedirs(channel_dir)

        if settings.FORMAT_XML:
            from xml.dom import minidom

            xml_str = ET.tostring(data, encoding="UTF-8", method="xml")
            reparsed = minidom.parseString(xml_str)
            pretty_xml = reparsed.toprettyxml(indent="  ", encoding="UTF-8")
            file_path = channel_dir + f"/{filename}.xml"
            with open(file_path, "wb") as f:
                f.write(pretty_xml)
        else:
            data = ET.tostring(data, encoding="UTF-8", method="xml")
            file_path = channel_dir + f"/{filename}.xml"

            with open(file_path, "wb") as f:
                f.write(data)

    def print_progress(self, written: int, total: int, name: str):
        """
        Wyświetla postęp operacji przy użyciu biblioteki tqdm.
        Metoda inicjalizuje pasek postępu tylko wtedy, gdy jest wywoływana po raz pierwszy.
        """
        if not hasattr(self, "_tqdm_bars"):
            self._tqdm_bars = {}

        if name not in self._tqdm_bars:
            self._tqdm_bars[name] = tqdm(
                total=total, desc=f"Przetwarzanie {name}", unit="element", leave=True, disable=None
            )
            self._tqdm_bars[name].update(written)
        else:
            last_update = getattr(self, f"_last_{name}_update", 0)
            self._tqdm_bars[name].update(written - last_update)

        setattr(self, f"_last_{name}_update", written)

        if written >= total:
            self._tqdm_bars[name].close()
            del self._tqdm_bars[name]

    def _add_log_params(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self.logger, "add_log_param"):
                self.logger.add_log_param(key, value)
            else:
                self.logger.info(f"Log param {key}: {value}")

    def save_merged_files(self):
        """Zapisuje połączone pliki sitemap (gdy merge_languages_in_sitemap=True)."""
        if not self.sitemap_channel.merge_languages_in_sitemap:
            return
        self._add_log_params(language="merged")

        if not self.merged_urlsets:
            self.logger.warning(f"No merged sitemap files to save for domain {self.domain_sitemap.idx}")
            self.logger.delete_log_param("language")
            return

        self.logger.info(f"Saving {len(self.merged_urlsets)} merged sitemap files for domain {self.domain_sitemap.idx}")
        for key, urlset in self.merged_urlsets.items():
            try:
                self.save_xml(urlset, key)
                self.logger.info(f"Successfully saved merged sitemap file: {key}")
            except Exception as e:
                self.logger.exception(e)

        self.merged_urlsets = {}
        self.logger.delete_log_param("language")

    def create_base_urlset(self) -> ET.Element:
        urlset = ET.Element("urlset")
        urlset.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")
        urlset.set("xmlns:xhtml", "http://www.w3.org/1999/xhtml")
        return urlset

    @abstractmethod
    def generate(self, **kwargs) -> None:
        pass
