# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

try:
    from django_sitemap.settings import CONTENTDB_PACKAGE, Content, ContentType, Draft, Language, Published, Route
except ImportError:
    pass

from django.db import models
from django.db.models import OuterRef, Q, Subquery


class ContentDBPage(models.Model):
    """
    A proxy model for ContentDB pages to be used in sitemap generation.
    This is not a real model, but a helper class to provide methods for sitemap generation.
    """

    class Meta:
        abstract = True

    @classmethod
    def get_active_drafts_pages(cls, language_iso2, access_rights: list[str] = None, content_types: list[str] = None):
        """
        Get all active published pages with routes
        """
        if Draft is None:
            return []

        drafts = (
            Draft.objects.select_related("content")
            .filter(routes__isnull=False)
            .filter(content__isnull=False, published__isnull=False)
            .filter(Q(language__iso2=language_iso2))
            .filter(content_type__slug__in=content_types)
        )
        if hasattr(ContentType, "is_layout_extender"):
            drafts = drafts.filter(content_type__is_layout_extender=False)

        if access_rights:
            filter_access_rights = []
            for access_right in access_rights:
                filter_access_rights.append(Q(access_rights__access_level=access_right))
            drafts = drafts.filter(*filter_access_rights, _connector=Q.OR).distinct()

        if hasattr(Route, "drafts"):
            drafts.annotate(
                routes_url=Subquery(
                    Route.objects.filter(drafts__in=OuterRef("pk")).values_list("url", flat=True).distinct(),
                    output_field=models.CharField(),
                )
            )
        else:
            drafts.annotate(
                routes_url=Subquery(
                    Route.objects.filter(draft__in=OuterRef("pk")).values_list("url", flat=True).distinct(),
                    output_field=models.CharField(),
                )
            )
        return drafts.distinct()
