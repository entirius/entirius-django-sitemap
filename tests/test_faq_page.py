# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for FaqPage.get_active_items() channel scoping."""

import pytest
from django_faq.models import FaqGroup, FaqItem

from django_sitemap.models.faq import FaqPage


@pytest.mark.django_db
def test_returns_empty_queryset_when_channel_is_none():
    items = FaqPage.get_active_items(channel=None)
    assert list(items) == []
    assert items.model is FaqItem


@pytest.mark.django_db
def test_ungrouped_active_item_is_included(faq_channel):
    FaqItem.objects.create(url_key="ungrouped", question="Q?", answer="A.", is_active=True)
    items = FaqPage.get_active_items(channel=faq_channel)
    keys = list(items.values_list("url_key", flat=True))
    assert "ungrouped" in keys


@pytest.mark.django_db
def test_inactive_item_is_excluded(faq_channel):
    FaqItem.objects.create(url_key="inactive-item", question="Q?", answer="A.", is_active=False)
    keys = list(FaqPage.get_active_items(channel=faq_channel).values_list("url_key", flat=True))
    assert "inactive-item" not in keys


@pytest.mark.django_db
def test_item_in_matching_channel_group_is_included(faq_channel):
    group = FaqGroup.objects.create(idx="general", name="General", is_active=True)
    group.channels.add(faq_channel)
    FaqItem.objects.create(url_key="grp-match", question="Q?", answer="A.", group=group, is_active=True)
    keys = list(FaqPage.get_active_items(channel=faq_channel).values_list("url_key", flat=True))
    assert "grp-match" in keys


@pytest.mark.django_db
def test_item_in_global_group_empty_channels_is_included(faq_channel):
    """Group with no channels assigned = global, visible in all channels."""
    group = FaqGroup.objects.create(idx="global", name="Global", is_active=True)
    # No channels assigned
    FaqItem.objects.create(url_key="grp-global", question="Q?", answer="A.", group=group, is_active=True)
    keys = list(FaqPage.get_active_items(channel=faq_channel).values_list("url_key", flat=True))
    assert "grp-global" in keys


@pytest.mark.django_db
def test_item_in_other_channel_group_is_excluded(faq_channel, other_faq_channel):
    """Item in group restricted to a different channel must not leak."""
    group = FaqGroup.objects.create(idx="usa-only", name="USA Only", is_active=True)
    group.channels.add(other_faq_channel)
    FaqItem.objects.create(url_key="usa-item", question="Q?", answer="A.", group=group, is_active=True)
    keys = list(FaqPage.get_active_items(channel=faq_channel).values_list("url_key", flat=True))
    assert "usa-item" not in keys


@pytest.mark.django_db
def test_item_in_inactive_group_is_excluded(faq_channel):
    group = FaqGroup.objects.create(idx="archived", name="Archived", is_active=False)
    group.channels.add(faq_channel)
    FaqItem.objects.create(url_key="archived-item", question="Q?", answer="A.", group=group, is_active=True)
    keys = list(FaqPage.get_active_items(channel=faq_channel).values_list("url_key", flat=True))
    assert "archived-item" not in keys


@pytest.mark.django_db
def test_distinct_no_duplicates_when_group_in_multiple_channels(faq_channel, other_faq_channel):
    """An item in a group assigned to multiple channels appears once."""
    group = FaqGroup.objects.create(idx="multi", name="Multi", is_active=True)
    group.channels.set([faq_channel, other_faq_channel])
    FaqItem.objects.create(url_key="multi-item", question="Q?", answer="A.", group=group, is_active=True)
    items = FaqPage.get_active_items(channel=faq_channel)
    matching = items.filter(url_key="multi-item")
    assert matching.count() == 1


@pytest.mark.django_db
def test_prefetches_translations_no_n_plus_one(faq_channel, django_assert_num_queries):
    """Translations are prefetched so the generator can resolve per-language url_key
    without firing one query per (item, language) pair."""
    from django_faq.models import FaqItemT9N

    lang_en = faq_channel.default_language
    for i in range(5):
        item = FaqItem.objects.create(url_key=f"item-{i}", question="Q?", answer="A.", is_active=True)
        FaqItemT9N.objects.create(item=item, language=lang_en, url_key=f"en-{i}", question="Q?", answer="A.")

    qs = FaqPage.get_active_items(channel=faq_channel)
    # Two queries total: one for items, one for the prefetched translations (with language).
    with django_assert_num_queries(2):
        for item in qs:
            _ = item.pk
            _ = item.url_key
            _ = item.modified_at
            for t9n in item.translations.all():
                _ = t9n.url_key
                _ = t9n.language.iso2
