# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest
from django_faq.models import FaqChannel
from django_regional.models import Language

from django_sitemap.models import Channel, DomainSitemap, LanguageSitemap


@pytest.fixture
def lang_en(db):
    return Language.objects.create(iso2="en", iso3="eng", name_en="English", name_pl="angielski")


@pytest.fixture
def lang_pl(db):
    return Language.objects.create(iso2="pl", iso3="pol", name_en="Polish", name_pl="polski")


@pytest.fixture
def faq_channel(db, lang_en, lang_pl):
    channel = FaqChannel.objects.create(idx="default-europe", name="Default Europe", default_language=lang_en)
    channel.languages.set([lang_en, lang_pl])
    return channel


@pytest.fixture
def other_faq_channel(db, lang_en):
    channel = FaqChannel.objects.create(idx="default-usa", name="Default USA", default_language=lang_en)
    channel.languages.set([lang_en])
    return channel


@pytest.fixture
def language_sitemap(db):
    return LanguageSitemap.objects.create(
        idx="default-europe",
        channel_short_idx="eu",
        product_url="{{language_iso2.lower()}}/p",
        category_url="{{language_iso2.lower()}}/c",
        faq_url="{{language_iso2.lower()}}/faq",
    )


@pytest.fixture
def sitemap_channel(db):
    return Channel.objects.create(idx="default-europe")


@pytest.fixture
def domain_sitemap(db, sitemap_channel, language_sitemap, lang_en, lang_pl):
    ds = DomainSitemap.objects.create(
        idx="europe-domain",
        channel=sitemap_channel,
        domain_url="https://example.com",
        language_sitemap=language_sitemap,
    )
    ds.languages.set([lang_en, lang_pl])
    return ds
