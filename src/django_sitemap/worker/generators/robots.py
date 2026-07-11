# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import shutil

from process_logger import ProcessLogger

from django_sitemap import settings
from django_sitemap.worker.generators.base import BaseSitemapGenerator


class RobotsTxtGenerator(BaseSitemapGenerator):
    def __init__(self, *args, **kwargs):
        super().__init__("robots", *args, **kwargs)
        self.set_logger(ProcessLogger("ROBOTS_TXT_GENERATOR", module="django_sitemap"))

        self.channels_sitemaps_dir = os.path.join(settings.SITEMAP_PATH, self.domain_sitemap.idx)
        self.robots_dir = os.path.join(self.channels_sitemaps_dir, "robots.txt")

    def copy_template(self):
        if self.sitemap_channel and self.sitemap_channel.robots_txt:
            with open(self.robots_dir, "w") as f:
                f.write(self.sitemap_channel.robots_txt)
                if not self.sitemap_channel.robots_txt.endswith("\n"):
                    f.write("\n")
        else:
            shutil.copy(settings.ROBOTS_TEMPLATE_PATH, self.robots_dir)

    def add_sitemaps_to_robots(self):
        base_url = self._get_base_url()
        with open(self.robots_dir, "a") as f:
            ignore = ["robots.txt", ".sitemap-processing"]
            for filename in os.listdir(self.channels_sitemaps_dir):
                if filename not in ignore:
                    f.write(f"Sitemaps: {base_url}/sitemap/{filename}\n")

    def generate(self):
        self.ensure_sitemap_directory()
        self.copy_template()
        self.add_sitemaps_to_robots()
