import os
import sys
from django.core.wsgi import get_wsgi_application
from dotenv import load_dotenv, find_dotenv

find_dotenv()

class Application(object):

    def __call__(self, environ, start_response):

        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.append(BASE_DIR)

        try:
            dotenv_path
            load_dotenv(dotenv_path)
            #print('Loading doetenv_path')
        except NameError:
            #print('dotenv_path not defined.')
            pass
            
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")

        _application = get_wsgi_application()
        return _application(environ, start_response)

        #output = b'Hello World!'
        #start_response('200 OK',[('Content-type', 'text/plain')])
        #return [output]


sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..'))
application = Application()
