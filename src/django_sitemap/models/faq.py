# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models
from django.db.models import Prefetch, Q, QuerySet

try:
    from django_faq.models import FaqItemT9N
except ImportError:
    FaqItemT9N = None

try:
    from django_sitemap.settings import FaqChannel, FaqItem
except ImportError:
    FaqChannel = FaqItem = None


class FaqPage(models.Model):
    """Holds the scoping query for FAQ sitemap — mirrors item_service.list_items in ORM."""

    class Meta:
        abstract = True

    @classmethod
    def get_active_items(cls, channel) -> QuerySet:
        """
        Active FAQ items visible in `channel`. Scoping mirrors item_service.list_items:
          item.is_active = True
          AND (group is None OR (group.is_active AND (group.channels=channel OR group.channels empty)))

        Items come with translations prefetched (only the columns the sitemap generator
        needs to resolve per-language url_key with fallback to base item.url_key).

        Callers must not invoke this when django_faq is not installed — the generator
        guards on FAQ_PACKAGE before reaching this code path.
        """
        if channel is None:
            return FaqItem.objects.none()

        t9n_prefetch = Prefetch(
            "translations",
            queryset=FaqItemT9N.objects.select_related("language").only("pk", "item_id", "language__iso2", "url_key"),
        )
        return (
            FaqItem.objects.filter(is_active=True)
            .filter(
                Q(group__isnull=True)
                | (Q(group__is_active=True) & (Q(group__channels=channel) | Q(group__channels__isnull=True)))
            )
            .prefetch_related(t9n_prefetch)
            .distinct()
        )
