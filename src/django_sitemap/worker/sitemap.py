# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django_sitemap.models import DomainSitemap
from django_sitemap.worker.generators.sitemap_coordinator import SitemapCoordinator


def generate_sitemap(domain_sitemap: DomainSitemap):
    coordinator = SitemapCoordinator(domain_sitemap=domain_sitemap)
    coordinator.generate()


def generate_robots(domain_sitemap: DomainSitemap):
    coordinator = SitemapCoordinator(domain_sitemap=domain_sitemap)
    coordinator.generators["robots"].generate()
