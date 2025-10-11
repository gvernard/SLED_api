from mysite.settings_common import *

SECRET_KEY = 'django-insecure-3#$_(o_0g=w68gw@y5anq4$yb2$b!&1_@+bk%jse$*mboql#!t'

DEBUG = True

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

ALLOWED_HOSTS = ['127.0.0.1','127.0.1.1','localhost']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'strong_lenses_database',
        'USER': 'sled_root',
        'PASSWORD': '12345',
        'HOST': 'db',
        'PORT': '3306',
    }
}

FORCE_SCRIPT_NAME = '/'
STATIC_URL = 'staticfiles/'
STATIC_ROOT = '/static'
STATIC_LOCATION = 'static'

DATABASE_FILE_LOCATION = '/files'
MEDIA_URL = 'files/'
MEDIA_ROOT = '/files'
DEFAULT_FILE_STORAGE = 'mysite.storage_backends.LocalStorage'


# The following two variables are definted in settings_common but we need to extent them here
CSP_STYLE_SRC_ELEM.append('http://fonts.googleapis.com')
CSP_FONT_SRC.append('http://fonts.gstatic.com')

CELERY_BROKER_URL = 'redis://redis:6379'
CELERY_RESULT_BACKEND = 'redis://redis:6379'
