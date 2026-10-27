# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for FaqSitemapGenerator — guard paths, URL formatting, XML output."""

import os
import xml.etree.ElementTree as ET
from unittest import mock

import pytest
from django_faq.models import FaqItem, FaqItemT9N

from django_sitemap import settings as sitemap_settings
from django_sitemap.models import FileSplitMode
from django_sitemap.worker.generators.faq import FaqSitemapGenerator


@pytest.fixture
def generator(domain_sitemap):
    # BaseSitemapGenerator.__init__ calls _get_pim_shop; mock to skip PIM lookup.
    with mock.patch.object(FaqSitemapGenerator, "_get_pim_shop", return_value=None):
        gen = FaqSitemapGenerator(domain_sitemap=domain_sitemap)
    # _get_shop_languages relies on PIM Shop intersect; bypass to return domain languages
    gen._get_shop_languages = lambda: list(domain_sitemap.languages.values_list("iso2", flat=True))
    return gen


_SM_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def _read_urlset(xml_path):
    """Return list of <loc> texts from a sitemap XML file."""
    tree = ET.parse(xml_path)
    return [loc.text for loc in tree.getroot().findall(f"{_SM_NS}url/{_SM_NS}loc")]


def _read_lastmods(xml_path):
    """Return list of <lastmod> texts from a sitemap XML file."""
    tree = ET.parse(xml_path)
    return [el.text for el in tree.getroot().findall(f"{_SM_NS}url/{_SM_NS}lastmod")]


@pytest.mark.django_db
def test_generate_skips_when_faq_url_empty(generator, language_sitemap, tmp_path, monkeypatch):
    monkeypatch.setattr(sitemap_settings, "SITEMAP_PATH", str(tmp_path / "sitemap") + "/")
    monkeypatch.setattr(sitemap_settings, "TEMPORARY_PATH", str(tmp_path / "tmp") + "/")
    language_sitemap.faq_url = ""
    language_sitemap.save()
    generator.sitemap_channel.refresh_from_db()

    generator.generate()

    out_dir = tmp_path / "tmp" / "europe-domain"
    assert not out_dir.exists() or not list(out_dir.glob("django_faq-*.xml"))


@pytest.mark.django_db
def test_generate_skips_when_faq_package_missing(generator, tmp_path, monkeypatch):
    monkeypatch.setattr(sitemap_settings, "SITEMAP_PATH", str(tmp_path / "sitemap") + "/")
    monkeypatch.setattr(sitemap_settings, "TEMPORARY_PATH", str(tmp_path / "tmp") + "/")
    with mock.patch.object(sitemap_settings, "FAQ_PACKAGE", None):
        generator.generate()
    out_dir = tmp_path / "tmp" / "europe-domain"
    assert not out_dir.exists() or not list(out_dir.glob("django_faq-*.xml"))


@pytest.mark.django_db
def test_generate_skips_when_faq_channel_not_found(generator, language_sitemap, tmp_path, monkeypatch):
    monkeypatch.setattr(sitemap_settings, "SITEMAP_PATH", str(tmp_path / "sitemap") + "/")
    monkeypatch.setattr(sitemap_settings, "TEMPORARY_PATH", str(tmp_path / "tmp") + "/")
    generator.channel_idx = "nonexistent-channel"
    generator.generate()
    out_dir = tmp_path / "tmp" / "europe-domain"
    assert not out_dir.exists() or not list(out_dir.glob("django_faq-*.xml"))


@pytest.mark.django_db
def test_get_faq_base_url_substitutes_language(generator):
    assert generator._get_faq_base_url("en") == "https://example.com/en/faq/"
    assert generator._get_faq_base_url("pl") == "https://example.com/pl/faq/"


@pytest.mark.django_db
def test_get_faq_base_url_with_channel_short_idx(generator, language_sitemap):
    language_sitemap.faq_url = "{{channel_short_idx}}/{{language_iso2.lower()}}/faq"
    language_sitemap.save()
    generator.sitemap_channel.refresh_from_db()
    assert generator._get_faq_base_url("en") == "https://example.com/eu/en/faq/"


@pytest.mark.django_db
def test_generate_full_flow_produces_merged_xml(generator, faq_channel, language_sitemap, tmp_path, monkeypatch):
    monkeypatch.setattr(sitemap_settings, "SITEMAP_PATH", str(tmp_path / "sitemap") + "/")
    monkeypatch.setattr(sitemap_settings, "TEMPORARY_PATH", str(tmp_path / "tmp") + "/")
    language_sitemap.file_split_mode = FileSplitMode.WHOLE_CHANNEL
    language_sitemap.save()
    generator.sitemap_channel.refresh_from_db()

    FaqItem.objects.create(url_key="how-to-buy", question="Q1?", answer="A1.", is_active=True)
    FaqItem.objects.create(url_key="how-to-return", question="Q2?", answer="A2.", is_active=True)

    generator.generate()

    # Merged mode: single file with both languages × both items = 4 URLs
    out_dir = tmp_path / "tmp" / "europe-domain"
    files = sorted(os.listdir(out_dir))
    assert files == ["django_faq-1.xml"]

    locs = _read_urlset(out_dir / "django_faq-1.xml")
    assert sorted(locs) == sorted(
        [
            "https://example.com/en/faq/how-to-buy",
            "https://example.com/pl/faq/how-to-buy",
            "https://example.com/en/faq/how-to-return",
            "https://example.com/pl/faq/how-to-return",
        ]
    )

    lastmods = _read_lastmods(out_dir / "django_faq-1.xml")
    assert len(lastmods) == 4
    assert all("T" in v for v in lastmods)


@pytest.mark.django_db
def test_generate_writes_per_language_files_when_merge_disabled(
    generator, faq_channel, language_sitemap, tmp_path, monkeypatch
):
    monkeypatch.setattr(sitemap_settings, "SITEMAP_PATH", str(tmp_path / "sitemap") + "/")
    monkeypatch.setattr(sitemap_settings, "TEMPORARY_PATH", str(tmp_path / "tmp") + "/")
    language_sitemap.file_split_mode = FileSplitMode.PER_LANGUAGE
    language_sitemap.save()
    generator.sitemap_channel.refresh_from_db()

    FaqItem.objects.create(url_key="item-1", question="Q?", answer="A.", is_active=True)

    generator.generate()

    out_dir = tmp_path / "tmp" / "europe-domain"
    files = sorted(os.listdir(out_dir))
    assert files == ["django_faq-1-en.xml", "django_faq-1-pl.xml"]

    assert _read_urlset(out_dir / "django_faq-1-en.xml") == ["https://example.com/en/faq/item-1"]
    assert _read_urlset(out_dir / "django_faq-1-pl.xml") == ["https://example.com/pl/faq/item-1"]


@pytest.mark.django_db
def test_generate_skips_languages_when_no_active_items(generator, faq_channel, tmp_path, monkeypatch):
    monkeypatch.setattr(sitemap_settings, "SITEMAP_PATH", str(tmp_path / "sitemap") + "/")
    monkeypatch.setattr(sitemap_settings, "TEMPORARY_PATH", str(tmp_path / "tmp") + "/")
    generator.generate()
    out_dir = tmp_path / "tmp" / "europe-domain"
    assert not out_dir.exists() or not list(out_dir.glob("django_faq-*.xml"))


@pytest.mark.django_db
def test_lastmod_uses_item_modified_at(generator, faq_channel, language_sitemap, tmp_path, monkeypatch):
    monkeypatch.setattr(sitemap_settings, "SITEMAP_PATH", str(tmp_path / "sitemap") + "/")
    monkeypatch.setattr(sitemap_settings, "TEMPORARY_PATH", str(tmp_path / "tmp") + "/")
    language_sitemap.file_split_mode = FileSplitMode.PER_LANGUAGE
    language_sitemap.save()
    generator.sitemap_channel.refresh_from_db()

    item = FaqItem.objects.create(url_key="item-1", question="Q?", answer="A.", is_active=True)

    generator.generate()

    item.refresh_from_db()  # ensure DB-rounded value matches what generator read
    out_dir = tmp_path / "tmp" / "europe-domain"
    lastmods = _read_lastmods(out_dir / "django_faq-1-en.xml")
    assert lastmods == [item.modified_at.isoformat()]


@pytest.mark.django_db
def test_generate_excludes_inactive_items(generator, faq_channel, tmp_path, monkeypatch):
    monkeypatch.setattr(sitemap_settings, "SITEMAP_PATH", str(tmp_path / "sitemap") + "/")
    monkeypatch.setattr(sitemap_settings, "TEMPORARY_PATH", str(tmp_path / "tmp") + "/")

    FaqItem.objects.create(url_key="visible", question="Q?", answer="A.", is_active=True)
    FaqItem.objects.create(url_key="hidden", question="Q?", answer="A.", is_active=False)

    generator.generate()

    out_dir = tmp_path / "tmp" / "europe-domain"
    locs_en = _read_urlset(out_dir / "django_faq-1.xml")
    assert any("visible" in loc for loc in locs_en)
    assert not any("hidden" in loc for loc in locs_en)


# --- Per-language url_key resolution (django-faq 1.3.0+ FaqItemT9N.url_key) ---


@pytest.mark.django_db
def test_per_language_url_key_override_wins(
    generator, faq_channel, language_sitemap, lang_en, lang_pl, tmp_path, monkeypatch
):
    """Non-empty FaqItemT9N.url_key replaces base url_key in that language's URL."""
    monkeypatch.setattr(sitemap_settings, "SITEMAP_PATH", str(tmp_path / "sitemap") + "/")
    monkeypatch.setattr(sitemap_settings, "TEMPORARY_PATH", str(tmp_path / "tmp") + "/")
    language_sitemap.file_split_mode = FileSplitMode.PER_LANGUAGE
    language_sitemap.save()
    generator.sitemap_channel.refresh_from_db()

    item = FaqItem.objects.create(url_key="atrybucja-w-e-commerce", question="Q?", answer="A.", is_active=True)
    FaqItemT9N.objects.create(
        item=item,
        language=lang_en,
        url_key="what-is-attribution-for-an-online-store",
        question="EN Q?",
        answer="EN A.",
    )
    # No PL T9N row → PL falls back to base item.url_key

    generator.generate()

    out_dir = tmp_path / "tmp" / "europe-domain"
    assert _read_urlset(out_dir / "django_faq-1-en.xml") == [
        "https://example.com/en/faq/what-is-attribution-for-an-online-store"
    ]
    assert _read_urlset(out_dir / "django_faq-1-pl.xml") == ["https://example.com/pl/faq/atrybucja-w-e-commerce"]


@pytest.mark.django_db
def test_empty_t9n_url_key_falls_back_to_base(generator, faq_channel, language_sitemap, lang_en, tmp_path, monkeypatch):
    """FaqItemT9N row with url_key='' MUST NOT shadow the base url_key."""
    monkeypatch.setattr(sitemap_settings, "SITEMAP_PATH", str(tmp_path / "sitemap") + "/")
    monkeypatch.setattr(sitemap_settings, "TEMPORARY_PATH", str(tmp_path / "tmp") + "/")
    language_sitemap.file_split_mode = FileSplitMode.PER_LANGUAGE
    language_sitemap.save()
    generator.sitemap_channel.refresh_from_db()

    item = FaqItem.objects.create(url_key="how-to-return", question="Q?", answer="A.", is_active=True)
    FaqItemT9N.objects.create(item=item, language=lang_en, url_key="", question="EN Q?", answer="EN A.")

    generator.generate()

    out_dir = tmp_path / "tmp" / "europe-domain"
    assert _read_urlset(out_dir / "django_faq-1-en.xml") == ["https://example.com/en/faq/how-to-return"]


@pytest.mark.django_db
def test_no_t9n_row_uses_base_url_key(generator, faq_channel, language_sitemap, tmp_path, monkeypatch):
    """Item without any T9N rows uses base url_key for every language."""
    monkeypatch.setattr(sitemap_settings, "SITEMAP_PATH", str(tmp_path / "sitemap") + "/")
    monkeypatch.setattr(sitemap_settings, "TEMPORARY_PATH", str(tmp_path / "tmp") + "/")
    language_sitemap.file_split_mode = FileSplitMode.PER_LANGUAGE
    language_sitemap.save()
    generator.sitemap_channel.refresh_from_db()

    FaqItem.objects.create(url_key="base-only", question="Q?", answer="A.", is_active=True)

    generator.generate()

    out_dir = tmp_path / "tmp" / "europe-domain"
    assert _read_urlset(out_dir / "django_faq-1-en.xml") == ["https://example.com/en/faq/base-only"]
    assert _read_urlset(out_dir / "django_faq-1-pl.xml") == ["https://example.com/pl/faq/base-only"]


@pytest.mark.django_db
def test_per_language_url_key_in_merged_output(
    generator, faq_channel, language_sitemap, lang_en, lang_pl, tmp_path, monkeypatch
):
    """Per-language url_keys must be honoured in merged-language sitemap files too."""
    monkeypatch.setattr(sitemap_settings, "SITEMAP_PATH", str(tmp_path / "sitemap") + "/")
    monkeypatch.setattr(sitemap_settings, "TEMPORARY_PATH", str(tmp_path / "tmp") + "/")
    language_sitemap.file_split_mode = FileSplitMode.WHOLE_CHANNEL
    language_sitemap.save()
    generator.sitemap_channel.refresh_from_db()

    item = FaqItem.objects.create(url_key="cross-sell-vs-up-sell", question="Q?", answer="A.", is_active=True)
    FaqItemT9N.objects.create(
        item=item,
        language=lang_en,
        url_key="cross-sell-vs-up-sell-what-are-the-differences",
        question="EN Q?",
        answer="EN A.",
    )
    FaqItemT9N.objects.create(item=item, language=lang_pl, url_key="", question="PL Q?", answer="PL A.")

    generator.generate()

    out_dir = tmp_path / "tmp" / "europe-domain"
    locs = sorted(_read_urlset(out_dir / "django_faq-1.xml"))
    assert locs == [
        "https://example.com/en/faq/cross-sell-vs-up-sell-what-are-the-differences",
        "https://example.com/pl/faq/cross-sell-vs-up-sell",
    ]
