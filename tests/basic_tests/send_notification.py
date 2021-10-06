import os
import sys
import django

dirname = os.path.dirname(__file__)
base_dir = os.path.join(dirname,'../../')
sys.path.append(base_dir)

#Database init
os.environ['DJANGO_SETTINGS_MODULE'] = "mysite.settings"
django.setup()

# -----------------------------------------------------


from lenses.models import Users, SledGroups, Lenses
from notifications.signals import notify

actor = Users.objects.get(username='Cameron')

#print('hello')
notify.send(actor, recipient=actor, verb='you reached level 10')
