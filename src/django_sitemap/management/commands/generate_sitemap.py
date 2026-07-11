# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from argparse import BooleanOptionalAction

from django.core.management.base import BaseCommand

from django_sitemap.models import DomainSitemap
from django_sitemap.worker.sitemap import generate_robots, generate_sitemap


class Command(BaseCommand):
    help = """
    Generate sitemaps for products, categories, and ContentDB pages with multilingual support. Also generates a robots.txt file.
    Command processes all DomainSitemap entries if no domain_idx is provided.
    Command creates sitemap for languages defined in DomainSitemap.languages.
    """

    def add_arguments(self, parser):
        parser.add_argument("--domain_idx", type=str, help="Idx of DomainSitemap to generate for")
        parser.add_argument(
            "--sitemap", type=bool, action=BooleanOptionalAction, help="Only generate bundle sitemap", default=None
        )
        parser.add_argument(
            "--robots", type=bool, action=BooleanOptionalAction, help="Only generate robots.txt", default=None
        )

    def handle(self, *args, **options):
        domain_idx = options["domain_idx"]

        sitemap_flag = options["sitemap"]
        robots_flag = options["robots"]

        all_processes = [sitemap_flag, robots_flag]
        all_processes_is_none = all([x is None for x in all_processes])

        if False in all_processes:
            sitemap_flag = True if sitemap_flag is not False else False
            robots_flag = True if robots_flag is not False else False

        if True in all_processes:
            sitemap_flag = False if sitemap_flag is not True else True
            robots_flag = False if robots_flag is not True else True

        if all_processes_is_none:
            sitemap_flag = True
            robots_flag = True

        domain_sitemaps = DomainSitemap.objects.select_related("channel", "language_sitemap").prefetch_related(
            "languages"
        )

        if domain_idx:
            domain_sitemaps = domain_sitemaps.filter(idx=domain_idx)

        if not domain_sitemaps:
            self.stdout.write(self.style.ERROR("No DomainSitemap entries found"))
            return

        if sitemap_flag:
            for ds in domain_sitemaps:
                self.stdout.write(f"Generating sitemap for domain {ds.idx} ({ds.domain_url})")
                generate_sitemap(ds)

        if robots_flag:
            for ds in domain_sitemaps:
                self.stdout.write(f"Generating robots.txt for domain {ds.idx} ({ds.domain_url})")
                generate_robots(ds)

        self.stdout.write(self.style.SUCCESS("Sitemap generation completed successfully"))
