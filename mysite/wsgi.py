import os
from django.core.wsgi import get_wsgi_application
#import dotenv

#exec(open("./sled-production-envvars.py").read())

#if os.path.exists('sled-envvars.env'):
#    dotenv.read_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

application = get_wsgi_application()
