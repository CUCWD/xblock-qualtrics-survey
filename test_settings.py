"""Settings for standalone unit tests, separate from LMS runtime configuration."""
from test_utils.platform_stubs import install

install()

SECRET_KEY = 'standalone-tests-only'
USE_TZ = True
TIME_ZONE = 'UTC'
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sites',
    'organizations',
    'qualtricssurvey',
)
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'APP_DIRS': True}]
LMS_ROOT_URL = 'https://lms.example.org'
