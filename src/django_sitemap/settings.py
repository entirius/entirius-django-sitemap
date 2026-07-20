# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
from pathlib import Path

from django.conf import settings

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIRS = os.path.join(BASE_DIR, "django_sitemap/templates/admin/")

#
# Sitemap
#

URL_HOST = getattr(settings, "SITEMAP_URL_HOST", None)
if URL_HOST and URL_HOST.endswith("/"):
    URL_HOST = URL_HOST[:-1]

FORMAT_XML = getattr(settings, "SITEMAP_FORMAT_XML", True)

LIMIT = getattr(settings, "SITEMAP_LIMIT", 2000)
SITEMAP_ROOT_DIR = getattr(settings, "SITEMAP_ROOT_DIR", settings.MEDIA_ROOT)
SITEMAP_PATH = os.path.join(SITEMAP_ROOT_DIR, "sitemap/")
TEMPORARY_PATH = os.path.join(SITEMAP_ROOT_DIR, "sitemap-processing/")

SITEMAP_TEMPLATE = os.path.join(TEMPLATE_DIRS, "sitemap.xml")
ROBOTS_TEMPLATE_PATH = getattr(settings, "SITEMAP_ROBOTS_TEMPLATE_PATH", os.path.join(TEMPLATE_DIRS, "robots.txt"))

LIST_OF_CATEGORY_IDXES_WHICH_ARE_EXCLUDED = getattr(settings, "LIST_OF_CATEGORY_IDXES_WHICH_ARE_EXCLUDED", [])


try:
    from django_contentdb.models.content_type import ContentType
    from django_contentdb.models.draft import Draft
    from django_contentdb.models.language import Language
    from django_contentdb.models.published import Published
    from django_contentdb.models.route import Route

    CONTENTDB_PACKAGE = "django_contentdb"
except ImportError:
    try:
        from contentdb.models import ContentType, Draft, Language, Published, Route

        CONTENTDB_PACKAGE = "contentdb"
    except ImportError:
        CONTENTDB_PACKAGE = None


try:
    from django_faq.models import FaqChannel, FaqGroup, FaqItem

    FAQ_PACKAGE = "django_faq"
except ImportError:
    FaqChannel = FaqGroup = FaqItem = None
    FAQ_PACKAGE = None
