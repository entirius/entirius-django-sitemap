# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Soft-dependency wrapper around django-pricemanager for currency-based product filtering.

Isolated here (single call site) so the rest of the module stays decoupled and the query is
trivially mockable in tests. The import is lazy so this module always imports cleanly, even in
environments where django-pricemanager is installed but not in INSTALLED_APPS (e.g. the sitemap
test settings) — importing its models there raises RuntimeError, not ImportError.
"""


def get_skus_priced_in_currency(channel_idx: str, currency_iso3: str) -> set[str] | None:
    """Return SKUs that have a READY price in ``currency_iso3`` for ``channel_idx``.

    The currency is matched by ISO code (``django_regional.Currency.iso3`` == pricemanager
    ``Currency.code``). Returns ``None`` when django-pricemanager is unavailable (not installed,
    or not registered in INSTALLED_APPS), signalling that currency filtering cannot be applied.
    """
    try:
        from django_pricemanager.models import PriceListStatusEnum, ProductRepresentation
    except (ImportError, RuntimeError):
        return None

    return set(
        ProductRepresentation.objects.filter(
            prices__pricelist__sale_channel__channel__idx=channel_idx,
            prices__pricelist__currency__code=currency_iso3.upper(),
            prices__pricelist__status=PriceListStatusEnum.READY,
        )
        .values_list("sku", flat=True)
        .distinct()
    )
