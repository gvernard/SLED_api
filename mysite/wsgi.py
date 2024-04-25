import os
from django.core.wsgi import get_wsgi_application

#os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
#application = get_wsgi_application()

os.environ['DJANGO_SETTINGS_MODULE'] = 'mysite.settings'

exec(open("./sled-production-envvars.py").read())

application = get_wsgi_application()
