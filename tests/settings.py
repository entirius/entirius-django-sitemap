# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import tempfile

import dj_database_url

SECRET_KEY = "not so secret test secret"
TMP_DIR = tempfile.gettempdir()
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(TMP_DIR, "sitemap_test_media")
STATIC_URL = "/static/"
DEBUG = True
ALLOWED_HOSTS = ["*"]

# django-sitemap settings
SITEMAP_LIMIT = 100
SITEMAP_ROOT_DIR = os.path.join(TMP_DIR, "sitemap_test")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django_regional",
    "django_contentdb",  # django_sitemap.settings side-effect-imports its models
    "django_pim",  # django_sitemap generators module-level import ProductCategory/Product
    "django_faq",
    "django_sitemap",
]

MIDDLEWARE = []

# Postgres via DATABASE_URL (CI provides a postgres service; locally point it
# at any postgres 15+ — the default matches the CI service).
DATABASES = {
    "default": dj_database_url.config(default="postgresql://postgres:postgres@localhost:5432/test"),
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
