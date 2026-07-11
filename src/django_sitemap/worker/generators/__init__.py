"""
Sitemap generators package.
This package contains generator classes for creating sitemaps for different content types.
"""

from django_sitemap.worker.generators.base import BaseSitemapGenerator
from django_sitemap.worker.generators.category import CategorySitemapGenerator
from django_sitemap.worker.generators.product import ProductSitemapGenerator
from django_sitemap.worker.generators.robots import RobotsTxtGenerator
from django_sitemap.worker.generators.sitemap_coordinator import SitemapCoordinator

__all__ = [
    "BaseSitemapGenerator",
    "ProductSitemapGenerator",
    "CategorySitemapGenerator",
    "RobotsTxtGenerator",
    "SitemapCoordinator",
]
