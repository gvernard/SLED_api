"""
Django settings for mysite project.

Generated by 'django-admin startproject' using Django 3.2.3.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""
from django.db.backends.signals import connection_created
from django.dispatch import receiver
from django.db.models import Aggregate
from pathlib import Path
import os
import math
import socket

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-3#$_(o_0g=w68gw@y5anq4$yb2$b!&1_@+bk%jse$*mboql#!t'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['django01.obs.unige.ch', '127.0.0.1']

AUTH_USER_MODEL = 'lenses.Users'
GUARDIAN_MONKEY_PATCH = False
DJANGO_NOTIFICATIONS_CONFIG = { 'USE_JSONFIELD': True}
EMAIL_HOST = 'localhost'
EMAIL_PORT = 1025
#EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'guardian',
    'registration.apps.RegistrationConfig',  
    'crispy_forms',
    'notifications',
    'api',
    'rest_framework',
    'gm2m',
    'widget_tweaks',
    'bootstrap_modal_forms',
    'sled_collections',
    'sled_admin_collections',
    'sled_notifications',
    'sled_data',
    'sled_tasks',
    'sled_queries',
    'sled_instrument',
    'sled_band',
    'sled_papers',
    'lenses.apps.LensesConfig',
    'sled_groups.apps.GroupsConfig',
    'home.apps.HomeConfig',
    'sled_users.apps.UsersConfig',
    'actstream',
    'multiselectfield',
    'django_select2',
]

SITE_ID = 1

ACCOUNT_ACTIVATION_DAYS = 7 # One-week activation window

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend', # this is default
    'guardian.backends.ObjectPermissionBackend',
)

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'mysite.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates'),],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            'libraries': {
                'project_tags': 'templatetags.sled_extras'
            },
        },
    },
]



WSGI_APPLICATION = 'mysite.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

which_database="remote-mysql"

if which_database == "local-sqlite":
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
elif which_database == "remote-mysql":
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'OPTIONS': {
                'read_default_file': os.path.join(BASE_DIR, 'sensitive_db_scripts/remote-mysql.cnf'),
            }
        }
    }
elif which_database == "local-mysql":
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'OPTIONS': {
                'read_default_file': os.path.join(BASE_DIR, 'sensitive_db_scripts/local-mysql.cnf'),
            }
        }
    }
else:
    raise "Unknown database option: "+which_database


# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True



# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Media files, i.e. user uploaded files
MEDIA_ROOT  = os.path.join(BASE_DIR,'media')
MEDIA_URL = '/media/'
DATA_UPLOAD_MAX_NUMBER_FIELDS = None
FILE_UPLOAD_MAX_MEMORY_SIZE = 15242880
DATA_UPLOAD_MAX_MEMORY_SIZE = None

ACTSTREAM_SETTINGS = {
    'FETCH_RELATIONS': True,
    'USE_PREFETCH': True,
    'USE_JSONFIELD': True,
    'GFK_FETCH_DEPTH': 1,
}


LOGIN_URL = '/login/'
LOGOUT_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'


REDIS_HOST = 'localhost'
REDIS_PORT = '6379'
BROKER_URL = 'redis://' + REDIS_HOST + ':' + REDIS_PORT + '/0'
BROKER_TRANSPORT_OPTIONS = {'visibility_timeout': 3600} 
CELERY_RESULT_BACKEND = 'redis://' + REDIS_HOST + ':' + REDIS_PORT + '/0'


if socket.gethostname()=='django01':
    FORCE_SCRIPT_NAME = '/Research/twin_lenses'
    #SUB_SITE = '/Research/twin_lenses'
    #URL_PREFIX = '/Research/twin_lenses'

    STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
    STATIC_URL = '/Research/twin_lenses/static/'
    STATICFILES_DIRS = [
        os.path.join(BASE_DIR, 'static'),
    ]    

    LOGIN_URL = '/Research/twin_lenses/login/'
    LOGIN_REDIRECT_URL = '/Research/twin_lenses/'
    
    LOGOUT_URL = '/Research/twin_lenses/login/'
    LOGOUT_REDIRECT_URL = '/Research/twin_lenses/login/'


# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'





### Here I load my user function to the sqlite database in every connection
def mydistance(ra1,dec1,ra2,dec2):
    """
    Same implementation as in lenses.py and distance_on_sky.sql
    """
    dec1_rad = math.radians(float(dec1))
    dec2_rad = math.radians(float(dec2))
    Ddec = abs(dec1_rad - dec2_rad);
    Dra = abs(math.radians(float(ra1)) - math.radians(float(ra2)));
    a = math.pow(math.sin(Ddec/2.0),2) + math.cos(dec1_rad)*math.cos(dec2_rad)*math.pow(math.sin(Dra/2.0),2);
    d = math.degrees( 2.0*math.atan2(math.sqrt(a),math.sqrt(1.0-a)) )
    return d*3600.0

@receiver(connection_created)
def extend_sqlite(connection = None, ** kwargs):
    if connection.vendor == "sqlite":
        connection.connection.create_function("distance_on_sky",4,mydistance)
