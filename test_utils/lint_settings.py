"""Initialize Django for static analysis without importing LMS service doubles."""
SECRET_KEY = 'static-analysis-only'
INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'organizations',
)
