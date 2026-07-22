# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import xml.etree.ElementTree as ET
from datetime import UTC, datetime

from process_logger import ProcessLogger

from django_sitemap import settings
from django_sitemap.worker.generators.base import BaseSitemapGenerator


class IndexSitemapGenerator(BaseSitemapGenerator):
    """
    Per-domain sitemap index (`sitemap.xml`).

    Runs after the content generators (product/category/contentdb/faq), reading the temporary
    directory they wrote into, and emits a <sitemapindex> listing every generated sitemap file
    (all languages/currencies/countries). Each entry points at ``{base_url}/sitemap/{filename}``,
    matching the URL scheme used by RobotsTxtGenerator.
    """

    INDEX_NAME = "sitemap"  # -> sitemap.xml

    def __init__(self, *args, **kwargs):
        super().__init__("index", *args, **kwargs)
        self.set_logger(ProcessLogger("INDEX_SITEMAP_GENERATOR", module="django_sitemap"))
        self.temp_dir = os.path.join(settings.TEMPORARY_PATH, self.domain_sitemap.idx)

    def _list_sitemap_files(self) -> list[str]:
        """Every generated sitemap .xml in the domain's temp dir, excluding the index itself."""
        if not os.path.exists(self.temp_dir):
            return []
        return sorted(
            name for name in os.listdir(self.temp_dir) if name.endswith(".xml") and name != f"{self.INDEX_NAME}.xml"
        )

    def generate(self):
        files = self._list_sitemap_files()
        if not files:
            self.logger.warning(f"No sitemap files to index for domain {self.domain_sitemap.idx}")
            return

        base_url = self._get_base_url()
        sitemapindex = ET.Element("sitemapindex")
        sitemapindex.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")
        for filename in files:
            sitemap = ET.SubElement(sitemapindex, "sitemap")
            ET.SubElement(sitemap, "loc").text = f"{base_url}/sitemap/{filename}"
            mtime = os.path.getmtime(os.path.join(self.temp_dir, filename))
            ET.SubElement(sitemap, "lastmod").text = datetime.fromtimestamp(mtime, tz=UTC).isoformat()

        self.save_xml(sitemapindex, self.INDEX_NAME)
        self.logger.info(f"Saved sitemap index ({len(files)} entries) for domain {self.domain_sitemap.idx}")
