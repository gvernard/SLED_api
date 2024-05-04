#import os
#from django.core.wsgi import get_wsgi_application
#import dotenv

#exec(open("./sled-production-envvars.py").read())

#if os.path.exists('sled-envvars.env'):
#    dotenv.read_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

#os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
#print('hellp')
#application = get_wsgi_application()



def application(environ, start_response):
    import django
    from django.core.wsgi import get_wsgi_application
    import sys
    from django.core.handlers.wsgi import WSGIHandler
    import os

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

    get_wsgi_application()

    
'''
import os
def application(environ, start_response):
    if environ['mod_wsgi.process_group'] != '': 
        import signal
        os.kill(os.getpid(), signal.SIGINT)
    return ["killed"]

'''
