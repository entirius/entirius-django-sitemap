# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import shutil
from datetime import datetime

import pytz
from django.utils import timezone

from django_sitemap import settings
from django_sitemap.models import DomainSitemap
from django_sitemap.worker.generators.category import CategorySitemapGenerator
from django_sitemap.worker.generators.contentdb import ContentDBSitemapGenerator
from django_sitemap.worker.generators.faq import FaqSitemapGenerator
from django_sitemap.worker.generators.product import ProductSitemapGenerator
from django_sitemap.worker.generators.robots import RobotsTxtGenerator


class SitemapCoordinator:
    """
    Coordinator for the sitemap generation process.
    Manages the overall generation process and coordinates individual generators.
    """

    def __init__(self, domain_sitemap: DomainSitemap):
        self.domain_sitemap = domain_sitemap
        self.generators = {
            "product": ProductSitemapGenerator(domain_sitemap),
            "category": CategorySitemapGenerator(domain_sitemap),
            "contentdb": ContentDBSitemapGenerator(domain_sitemap),
            "faq": FaqSitemapGenerator(domain_sitemap),
            "robots": RobotsTxtGenerator(domain_sitemap),
        }
        self.channel_temp_dir = os.path.join(settings.TEMPORARY_PATH, domain_sitemap.idx)
        self.channel_dir = os.path.join(settings.SITEMAP_PATH, domain_sitemap.idx)

    def get_timezone(self) -> pytz.timezone:
        timezone_name = settings.TIMEZONE
        try:
            return pytz.timezone(timezone_name)
        except pytz.exceptions.UnknownTimeZoneError:
            return pytz.timezone("Europe/Warsaw")

    def get_current_time(self) -> datetime:
        tz = self.get_timezone()
        utc_tz = pytz.timezone("UTC")
        now = timezone.now().replace(tzinfo=utc_tz)
        return now.astimezone(tz)

    def check_settings(self):
        errors = []
        if settings.LIMIT is None:
            errors.append("SITEMAP_LIMIT")

        if errors:
            raise ValueError(f"You have to setup {', '.join(errors)} in service settings_local.py")

    def prepare_temporary_channel_directory(self):
        if not os.path.exists(settings.SITEMAP_PATH):
            os.makedirs(settings.SITEMAP_PATH)

        if not os.path.exists(settings.TEMPORARY_PATH):
            os.makedirs(settings.TEMPORARY_PATH)

        if not os.path.exists(self.channel_temp_dir):
            os.makedirs(self.channel_temp_dir)

    def move_to_final_directory(self):
        if os.path.exists(self.channel_dir):
            shutil.rmtree(self.channel_dir)

        os.rename(self.channel_temp_dir, self.channel_dir)

    def generate(self):
        self.check_settings()
        self.prepare_temporary_channel_directory()
        self.generators["product"].generate()
        self.generators["category"].generate()
        self.generators["contentdb"].generate()
        self.generators["faq"].generate()
        self.move_to_final_directory()
