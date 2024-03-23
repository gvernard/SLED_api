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
MEDIA_ROOT = '/files'
STATIC_ROOT = '/static'
