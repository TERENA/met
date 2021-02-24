#################################################################
# MET v2 Metadate Explorer Tool
#
# This Software is Open Source. See License: https://github.com/TERENA/met/blob/master/LICENSE.md
# Copyright (c) 2012, TERENA All rights reserved.
#
# This Software is based on MET v1 developed for TERENA by Yaco Sistemas, http://www.yaco.es/
# MET v2 was developed for TERENA by Tamim Ziai, DAASI International GmbH, http://www.daasi.de
# Current version of MET has been revised for performance improvements by Andrea Biancini,
# Consortium GARR, http://www.garr.it
##########################################################################

# Django settings for met project.

import os

try:
    from local_settings import HOSTNAME, BASEURL, BASEDIR, DEBUG, PROFILE, TEMPLATE_DEBUG, DATABASES, MYSQLPOOL_BACKEND, MYSQLPOOL_ARGUMENTS
    from local_settings import ADMINS, INTERNAL_IPS, ALLOWED_HOSTS, CACHES
    from local_settings import SAML_CREATE_UNKNOWN_USER, SAML_DJANGO_USER_MAIN_ATTRIBUTE, SAML_ATTRIBUTE_MAPPING, ORGANIZATION_NAME, SAML2DIR
    from local_settings import LOGIN_URL, LOGOUT_URL, SAML_DESCRIPTION, SAML_ENTITYID, SAML_CONFIG, DJANGO_FEDERATIONS, DJANGO_ADDITIONAL_IDPS
    from local_settings import MAIL_CONFIG, SLACK_CONFIG, OWA_BASEURL, OWA_SITEID
except Exception:
    raise
    print("Error in loading local_settings")

MANAGERS = ADMINS

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'Europe/Rome'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = os.path.join(BASEDIR, 'met', 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '%s/media/' % BASEURL

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.join(BASEDIR, 'met', 'static')

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '%s/static/' % BASEURL

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(BASEDIR, 'static'),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    #    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'wcc$cfn0p!+@kv%@9y^u3^6fax5_a-n84^o*gl94!%kqc!fm-n'

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    #'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'pagination.middleware.PaginationMiddleware',
]

if PROFILE:
    MIDDLEWARE_CLASSES.insert(1, 'silk.middleware.SilkyMiddleware')

ROOT_URLCONF = 'met.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'met.wsgi.application'

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'pagination',
    'met.portal',
    'met.metadataparser',
    'djangosaml2',
    'chartit',
]

if PROFILE:
    INSTALLED_APPS.append('silk')
    SILKY_META = True
    SILKY_PYTHON_PROFILER = True
    SILKY_INTERCEPT_PERCENT = 100
    # SILKY_AUTHENTICATION = True
    # SILKY_AUTHORISATION = True

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'saml2file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': '/var/log/djangosaml2.log',
            'formatter': 'verbose',
        }
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'ERROR',
        },
        #'django.request': {
        #    'handlers': ['mail_admins'],
        #    'level': 'ERROR',
        #    'propagate': True,
        #},
        'djangosaml2': {
            'handlers': ['saml2file'],
            'level': 'ERROR',
        },
        'silk': {
            'handlers': ['console'],
            'level': 'ERROR',
        },
    }
}

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    # 'django.core.context_processors.debug',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.tz',
    'django.core.context_processors.request',
    'django.contrib.messages.context_processors.messages',
    'met.portal.context_processors.portal_settings',
    'met.metadataparser.context_processors.nav_search_form',
)

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'djangosaml2.backends.Saml2Backend',
)

PAGE_LENGTH = 25

TOP_LENGTH = 3

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(BASEDIR, 'met/metadataparser/templates'),
)

CELERY_RESULT_BACKEND = 'djcelery.backends.database:DatabaseBackend'

TEST_RUNNER = 'django.test.runner.DiscoverRunner'

STATS = {
    # Features that have to be saved in the database
    'features': {
        'sp': 'SPSSODescriptor',
        'idp': 'IDPSSODescriptor',
        'aa': 'AASSODescriptor',
        'sp_saml1': 'urn:oasis:names:tc:SAML:1.1:protocol',
        'sp_saml2': 'urn:oasis:names:tc:SAML:2.0:protocol',
        'sp_shib1': 'urn:mace:shibboleth:1.0',
        'idp_saml1': 'urn:oasis:names:tc:SAML:1.1:protocol',
        'idp_saml2': 'urn:oasis:names:tc:SAML:2.0:protocol',
        'idp_shib1': 'urn:mace:shibboleth:1.0',
    },

    # Protocols
    'protocols': ['saml1', 'saml2', 'shib1'],

    # Feature names
    'feature_names': {
        'sp': 'SP',
        'idp': 'IDP',
        'aa': 'AA',
        'sp_saml1': 'SP SAML 1.1',
        'sp_saml2': 'SP SAML 2.0',
        'sp_shib1': 'SP Shibboleth 1.0',
        'idp_saml1': 'IDP SAML 1.1',
        'idp_saml2': 'IDP SAML 2.0',
        'idp_shib1': 'IDP Shibboleth 1.0',
    },

    # Statistics that can be shown (values are keys for 'features')
    'statistics': {
        'entity_by_type': {
            'terms': ['aa', 'sp', 'idp'],
            'title': 'Services',
            'x_title': 'Time',
            'y_title': 'Count'
        },
        'entity_by_protocol': {
            'terms': ['sp_saml1', 'sp_saml2', 'sp_shib1', 'idp_saml1', 'idp_saml2', 'idp_shib1'],
            'title': 'Protocols',
            'x_title': 'Time',
            'y_title': 'Count'
        },
    },

    # Time format in the x axis
    'time_format': '%d/%m/%Y',
}
