import os
import sys
from django.core.wsgi import get_wsgi_application


class Application(object):

    def __call__(self, environ, start_response):

        os.environ['SLED_PROD'] = environ['SLED_PROD']
        if os.environ['SLED_PROD'] == 'true':
            os.environ['S3_ENDPOINT_URL'] = environ['S3_ENDPOINT_URL']
            os.environ['DJANGO_SLACK_API_TOKEN'] = environ['DJANGO_SLACK_API_TOKEN']
            os.environ['DJANGO_EMAIL_PASSWORD'] = environ['DJANGO_EMAIL_PASSWORD']
            os.environ['DJANGO_DB_FILE'] = environ['DJANGO_DB_FILE']
            os.environ['DJANGO_SECRET_KEY'] = environ['DJANGO_SECRET_KEY']
            os.environ['S3_ACCESS_KEY_ID'] = environ['S3_ACCESS_KEY_ID']
            os.environ['S3_SECRET_ACCESS_KEY'] = environ['S3_SECRET_ACCESS_KEY']
            os.environ['S3_STORAGE_BUCKET_NAME'] = environ['S3_STORAGE_BUCKET_NAME']
            os.environ['S3_ENDPOINT_URL'] = environ['S3_ENDPOINT_URL']
            os.environ['DJANGO_NO_LAST_LOGIN'] = 'true'

        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.append(BASE_DIR)
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")

        _application = get_wsgi_application()
        return _application(environ, start_response)

        #output = b'Hello World!'
        #start_response('200 OK',[('Content-type', 'text/plain')])
        #return [output]


sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..'))
application = Application()
