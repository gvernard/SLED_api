import os
from mysite.settings_common import *
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

SECRET_KEY = os.environ['DJANGO_SECRET_KEY']

DEBUG = False
ADMINS = [('Giorgos','gvernardos@amnh.org')]
SERVER_EMAIL = 'sled-no-reply@sled.amnh.org'

#EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
#EMAIL_HOST_USER = 'sleddatabase@gmail.com'
#EMAIL_HOST_PASSWORD = os.environ['DJANGO_EMAIL_PASSWORD']
EMAIL_HOST = os.environ['DJANGO_EMAIL_HOST']
EMAIL_PORT = os.environ['DJANGO_EMAIL_PORT']
EMAIL_USE_TLS = False
EMAIL_USE_SSL = False

ALLOWED_HOSTS = ['127.0.0.1','127.0.1.1','localhost','sled.amnh.org','216.73.242.43']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'OPTIONS': {
            'read_default_file': os.environ['DJANGO_DB_FILE'],
        }
    }
}


AWS_ACCESS_KEY_ID = os.environ['S3_ACCESS_KEY_ID']
AWS_SECRET_ACCESS_KEY = os.environ['S3_SECRET_ACCESS_KEY']
AWS_STORAGE_BUCKET_NAME = os.environ['S3_STORAGE_BUCKET_NAME']
AWS_S3_ENDPOINT_URL = os.environ['S3_ENDPOINT_URL']
AWS_DEFAULT_ACL = None
AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}

STATIC_LOCATION = 'static'
STATIC_URL = f'{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/{STATIC_LOCATION}/'
STATICFILES_STORAGE = 'mysite.storage_backends.StaticStorage'

DATABASE_FILE_LOCATION = 'files'
MEDIA_URL = f'{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/{DATABASE_FILE_LOCATION}/'
DEFAULT_FILE_STORAGE = 'mysite.storage_backends.DatabaseFileStorage'


# The following two variables are definted in settings_common but we need to extent them here
CSP_STYLE_SRC_ELEM.append('https://fonts.googleapis.com')
CSP_FONT_SRC.append('https://fonts.gstatic.com')
