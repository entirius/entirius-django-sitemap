# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for LanguageSitemap.save() URL slash normalization."""

import pytest

from django_sitemap.models import LanguageSitemap


@pytest.mark.django_db
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("/foo/faq/", "foo/faq"),
        ("/foo/faq", "foo/faq"),
        ("foo/faq/", "foo/faq"),
        ("foo/faq", "foo/faq"),
        ("{{language_iso2.lower()}}/faq", "{{language_iso2.lower()}}/faq"),
    ],
)
def test_faq_url_slashes_trimmed(raw, expected):
    ls = LanguageSitemap.objects.create(idx=f"test-{raw}", faq_url=raw)
    ls.refresh_from_db()
    assert ls.faq_url == expected


@pytest.mark.django_db
def test_faq_url_empty_stays_none():
    ls = LanguageSitemap.objects.create(idx="empty")
    ls.refresh_from_db()
    assert ls.faq_url is None


@pytest.mark.django_db
def test_product_url_unaffected_by_faq_field():
    """Adding faq_url should not change behavior of other URL fields."""
    ls = LanguageSitemap.objects.create(idx="check-prod", product_url="/pl/p/", faq_url="/pl/faq/")
    ls.refresh_from_db()
    assert ls.product_url == "pl/p"
    assert ls.faq_url == "pl/faq"
